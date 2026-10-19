import { APP_NAME } from '../config'

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="logo">
      <img src="/logo.svg" width={size} height={size} alt="" />
      <span className="logo-text">{APP_NAME}</span>
    </span>
  )
}
