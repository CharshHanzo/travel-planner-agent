export function validateRequired(value: any): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim() !== ''
  if (Array.isArray(value)) return value.length > 0
  return true
}

export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function validateMinLength(value: string, min: number): boolean {
  return value.length >= min
}

export function validateMaxLength(value: string, max: number): boolean {
  return value.length <= max
}

export function validateNumber(value: any): boolean {
  return !isNaN(Number(value))
}

export function validatePositiveNumber(value: any): boolean {
  const num = Number(value)
  return !isNaN(num) && num > 0
}

export function validateDateRange(startDate: string, endDate: string): boolean {
  const start = new Date(startDate)
  const end = new Date(endDate)
  return start <= end
}
