# 5. Les e-mails envoyés à vos clients

Par défaut, Supabase envoie des e-mails en anglais, avec un expéditeur générique et une limite
de quelques e-mails par heure. Deux réglages à faire :

## A. Textes en français et en anglais

Supabase → **Authentication → Emails → Templates**. Remplacez le contenu :

### Confirm signup (confirmation d’inscription)
Sujet : `Confirmez votre compte Tradevantage / Confirm your account`
```html
<h2>Bienvenue sur Tradevantage !</h2>
<p>Cliquez sur le bouton pour confirmer votre adresse e-mail :</p>
<p><a href="{{ .ConfirmationURL }}" style="background:#2f6bff;color:#fff;padding:12px 20px;border-radius:999px;text-decoration:none">Confirmer mon compte</a></p>
<hr>
<h2>Welcome to Tradevantage!</h2>
<p>Click the button to confirm your email address:</p>
<p><a href="{{ .ConfirmationURL }}">Confirm my account</a></p>
<p style="color:#888;font-size:12px">Informations non contractuelles, ceci n’est pas un conseil en investissement.</p>
```

### Reset password (mot de passe oublié)
Sujet : `Nouveau mot de passe / New password — Tradevantage`
```html
<p>Vous avez demandé un nouveau mot de passe. Cliquez ici :</p>
<p><a href="{{ .ConfirmationURL }}" style="background:#2f6bff;color:#fff;padding:12px 20px;border-radius:999px;text-decoration:none">Choisir un nouveau mot de passe</a></p>
<p>Si vous n’êtes pas à l’origine de cette demande, ignorez cet e-mail.</p>
<hr>
<p>You asked for a new password: <a href="{{ .ConfirmationURL }}">choose a new password</a>.
If you didn’t ask for this, just ignore this email.</p>
```

## B. Un vrai expéditeur (avant l’ouverture au public)

Supabase → **Project Settings → Authentication → SMTP Settings** → activez *Custom SMTP*.
Un service gratuit pour commencer : **Brevo** (français, 300 e-mails/jour) ou **Resend**.
Expéditeur conseillé : `noreply@votredomaine.ch` (après l’achat du domaine).
