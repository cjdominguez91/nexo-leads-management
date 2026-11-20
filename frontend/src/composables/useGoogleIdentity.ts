const SCRIPT_URL = 'https://accounts.google.com/gsi/client'

let scriptPromise: Promise<void> | null = null

function loadGsiScript(): Promise<void> {
  if (scriptPromise) return scriptPromise

  scriptPromise = new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${SCRIPT_URL}"]`)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = SCRIPT_URL
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('No se pudo cargar Google Identity Services.'))
    document.head.appendChild(script)
  })

  return scriptPromise
}

export async function renderGoogleButton(
  container: HTMLElement,
  clientId: string,
  onCredential: (idToken: string) => void,
) {
  await loadGsiScript()
  const google = (window as any).google

  google.accounts.id.initialize({
    client_id: clientId,
    callback: (response: { credential: string }) => onCredential(response.credential),
  })

  google.accounts.id.renderButton(container, {
    theme: 'outline',
    size: 'large',
    width: 320,
  })
}
