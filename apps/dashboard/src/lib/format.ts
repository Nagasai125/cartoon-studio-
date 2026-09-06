export function formatGeneratedAt(value: string): string {
  const generatedAt = new Date(value)
  if (Number.isNaN(generatedAt.getTime())) return 'at an unknown time'

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
    day: 'numeric',
  }).format(generatedAt)
}

export function formatState(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
