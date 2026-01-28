import { useEffect } from "react"

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  callback: () => void
  description?: string
}

export function useKeyboardShortcut(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const matches =
          event.key === shortcut.key &&
          (shortcut.ctrlKey ?? false) === event.ctrlKey &&
          (shortcut.shiftKey ?? false) === event.shiftKey &&
          (shortcut.altKey ?? false) === event.altKey &&
          (shortcut.metaKey ?? false) === event.metaKey

        if (matches) {
          event.preventDefault()
          shortcut.callback()
          break
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [shortcuts])
}
