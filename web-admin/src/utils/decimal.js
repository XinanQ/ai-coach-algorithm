import Decimal from 'decimal.js-light'

export function decimal(value) {
  return new Decimal(value ?? 0)
}

export function decimalSum(values) {
  return values.reduce((sum, value) => sum.plus(decimal(value)), new Decimal(0))
}

export function decimalToNumber(value) {
  return decimal(value).toNumber()
}

export function decimalToFixed(value, decimals = 4) {
  return decimal(value).toFixed(decimals)
}
