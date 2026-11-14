//! Fenêtre de Sentinelle.
//!
//! Au démarrage : lance le serveur Python (le cerveau), ouvre la fenêtre et ajoute
//! une icône dans la barre des menus. Fermer la fenêtre la cache seulement ;
//! « Quitter » (menu de l'icône ou Cmd+Q) arrête tout, serveur compris.

use std::net::TcpStream;
#[cfg(debug_assertions)]
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager, RunEvent, WindowEvent};

const PORT: u16 = 8765;
const FENETRE: &str = "principale";

/// Le processus du serveur Python, pour pouvoir l'arrêter en quittant.
struct Serveur(Mutex<Option<Child>>);

fn serveur_deja_lance() -> bool {
    let adresse = ([127, 0, 0, 1], PORT).into();
    TcpStream::connect_timeout(&adresse, Duration::from_millis(300)).is_ok()
}

/// Mode développement : lance « python backend/main.py » depuis le code source.
#[cfg(debug_assertions)]
fn commande_serveur(_app: &AppHandle) -> Option<Command> {
    let racine = std::env::var("SENTINELLE_RACINE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join(".."));
    let python = std::env::var("SENTINELLE_PYTHON").map(PathBuf::from).unwrap_or_else(|_| {
        if cfg!(windows) {
            racine.join(".venv").join("Scripts").join("python.exe")
        } else {
            racine.join(".venv").join("bin").join("python")
        }
    });
    let mut commande = Command::new(python);
    commande.arg(racine.join("backend").join("main.py")).current_dir(&racine);
    Some(commande)
}

/// Application installée : lance le serveur empaqueté dans Sentinelle.app (dossier Resources/serveur).
#[cfg(not(debug_assertions))]
fn commande_serveur(app: &AppHandle) -> Option<Command> {
    let nom = if cfg!(windows) { "sentinelle-serveur.exe" } else { "sentinelle-serveur" };
    let dossier = app.path().resource_dir().ok()?.join("serveur");
    let mut commande = Command::new(dossier.join(nom));
    commande.current_dir(&dossier);
    Some(commande)
}

fn lancer_serveur(app: &AppHandle) -> Option<Child> {
    if serveur_deja_lance() {
        println!("[Sentinelle] Serveur déjà en ligne sur le port {PORT}.");
        return None;
    }
    let mut commande = commande_serveur(app)?;
    // Le journal technique du serveur va dans ~/Library/Logs/ch.sentinelle.app/serveur.log
    if let Ok(dossier) = app.path().app_log_dir() {
        let _ = std::fs::create_dir_all(&dossier);
        if let Ok(fichier) = std::fs::File::create(dossier.join("serveur.log")) {
            if let Ok(copie) = fichier.try_clone() {
                commande.stdout(Stdio::from(fichier)).stderr(Stdio::from(copie));
            }
        }
    }
    match commande.spawn() {
        Ok(enfant) => Some(enfant),
        Err(e) => {
            eprintln!("[Sentinelle] Impossible de lancer le serveur : {e}");
            None
        }
    }
}

fn montrer_fenetre(app: &AppHandle) {
    if let Some(fenetre) = app.get_webview_window(FENETRE) {
        let _ = fenetre.unminimize();
        let _ = fenetre.show();
        let _ = fenetre.set_focus();
    }
}

fn arreter_serveur(app: &AppHandle) {
    if let Some(etat) = app.try_state::<Serveur>() {
        if let Some(mut enfant) = etat.0.lock().unwrap().take() {
            let _ = enfant.kill();
            let _ = enfant.wait();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            app.manage(Serveur(Mutex::new(lancer_serveur(app.handle()))));

            // Icône dans la barre des menus
            let ouvrir = MenuItem::with_id(app, "ouvrir", "Ouvrir Sentinelle", true, None::<&str>)?;
            let quitter = MenuItem::with_id(app, "quitter", "Quitter Sentinelle", true, Some("CmdOrCtrl+Q"))?;
            let menu = Menu::with_items(app, &[&ouvrir, &quitter])?;
            let mut icone = TrayIconBuilder::with_id("sentinelle")
                .tooltip("Sentinelle")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, evenement| match evenement.id.as_ref() {
                    "ouvrir" => montrer_fenetre(app),
                    "quitter" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|icone, evenement| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = evenement
                    {
                        montrer_fenetre(icone.app_handle());
                    }
                });
            if let Some(image) = app.default_window_icon() {
                icone = icone.icon(image.clone());
            }
            icone.build(app)?;
            Ok(())
        })
        .on_window_event(|fenetre, evenement| {
            // Fermer la fenêtre = la cacher (Sentinelle reste dans la barre des menus).
            if let WindowEvent::CloseRequested { api, .. } = evenement {
                api.prevent_close();
                let _ = fenetre.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("Erreur au démarrage de Sentinelle");

    app.run(|app, evenement| match evenement {
        RunEvent::Exit => arreter_serveur(app),
        #[cfg(target_os = "macos")]
        RunEvent::Reopen { .. } => montrer_fenetre(app),
        _ => {}
    });
}
