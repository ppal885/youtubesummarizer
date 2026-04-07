import { Switch } from '@adobe/react-spectrum'
import { useTheme } from '../context/ThemeContext'

type Props = {
  /** Ignored — Spectrum switch has one size; kept for API compatibility */
  compact?: boolean
}

export function ThemeToggle(props: Props) {
  void props.compact
  const { isDark, setTheme } = useTheme()

  return (
    <Switch isSelected={isDark} onChange={(v) => setTheme(v ? 'dark' : 'light')}>
      Dark mode
    </Switch>
  )
}
