const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDateTime(value: string) {
  try {
    return dateTimeFormatter.format(new Date(value))
  } catch {
    return value
  }
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value)
}
