/**
 * Card validation utilities
 * Implements Luhn algorithm, expiry date validation, CVV validation, and field validation
 */

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface CardValidationResults {
  cardNumber: ValidationResult;
  expiryDate: ValidationResult;
  cvv: ValidationResult;
  cardholderName: ValidationResult;
  billingAddress: {
    street: ValidationResult;
    city: ValidationResult;
    state: ValidationResult;
    zipCode: ValidationResult;
    country: ValidationResult;
  };
  overall: ValidationResult;
}

/**
 * Luhn Algorithm: Validates credit card numbers
 * https://en.wikipedia.org/wiki/Luhn_algorithm
 */
export function validateCardNumberLuhn(cardNumber: string): ValidationResult {
  const errors: string[] = [];

  // Remove spaces and dashes
  const cleaned = cardNumber.replace(/[\s-]/g, "");

  // Check if it's all digits
  if (!/^\d+$/.test(cleaned)) {
    errors.push("Card number must contain only digits");
    return { isValid: false, errors };
  }

  // Check length (typically 13-19 digits)
  if (cleaned.length < 13 || cleaned.length > 19) {
    errors.push(`Card number must be between 13 and 19 digits (got ${cleaned.length})`);
    return { isValid: false, errors };
  }

  // Apply Luhn algorithm
  let sum = 0;
  let isEven = false;

  for (let i = cleaned.length - 1; i >= 0; i--) {
    let digit = parseInt(cleaned[i], 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  if (sum % 10 !== 0) {
    errors.push("Card number failed Luhn validation");
    return { isValid: false, errors };
  }

  return { isValid: true, errors: [] };
}

/**
 * Validate expiry date format and expiration
 * Expects MM/YY format
 */
export function validateExpiryDate(expiryDate: string): ValidationResult {
  const errors: string[] = [];

  // Check format MM/YY
  const dateRegex = /^(\d{2})\/(\d{2})$/;
  const match = expiryDate.trim().match(dateRegex);

  if (!match) {
    errors.push("Expiry date must be in MM/YY format");
    return { isValid: false, errors };
  }

  const month = parseInt(match[1], 10);
  const year = parseInt(match[2], 10);

  // Validate month
  if (month < 1 || month > 12) {
    errors.push(`Invalid month: ${month} (must be 01-12)`);
    return { isValid: false, errors };
  }

  // Check if card is expired
  const now = new Date();
  const currentYear = now.getFullYear() % 100; // Last 2 digits of current year
  const currentMonth = now.getMonth() + 1; // Months are 0-indexed

  // If year is in the past, it's expired
  if (year < currentYear) {
    errors.push(`Card expired (year ${year} is in the past)`);
    return { isValid: false, errors };
  }

  // If year is current, check month
  if (year === currentYear && month < currentMonth) {
    errors.push(`Card expired (month ${month}/${year} is in the past)`);
    return { isValid: false, errors };
  }

  return { isValid: true, errors: [] };
}

/**
 * Validate CVV format
 * CVV is typically 3-4 digits
 */
export function validateCVV(cvv: string): ValidationResult {
  const errors: string[] = [];

  const cleaned = cvv.trim().replace(/\s/g, "");

  // Check if it's all digits
  if (!/^\d+$/.test(cleaned)) {
    errors.push("CVV must contain only digits");
    return { isValid: false, errors };
  }

  // Check length (3-4 digits)
  if (cleaned.length < 3 || cleaned.length > 4) {
    errors.push(`CVV must be 3-4 digits (got ${cleaned.length})`);
    return { isValid: false, errors };
  }

  return { isValid: true, errors: [] };
}

/**
 * Validate cardholder name
 * Must be non-empty and contain at least 2 parts (first and last name)
 */
export function validateCardholderName(name: string): ValidationResult {
  const errors: string[] = [];

  const trimmed = name.trim();

  if (!trimmed) {
    errors.push("Cardholder name is required");
    return { isValid: false, errors };
  }

  // Check for at least 2 parts (first and last name)
  const parts = trimmed.split(/\s+/).filter((p) => p.length > 0);
  if (parts.length < 2) {
    errors.push("Cardholder name must include at least first and last name");
    return { isValid: false, errors };
  }

  // Check for valid characters (letters, spaces, hyphens, apostrophes)
  if (!/^[a-zA-Z\s\-']+$/.test(trimmed)) {
    errors.push("Cardholder name contains invalid characters");
    return { isValid: false, errors };
  }

  return { isValid: true, errors: [] };
}

/**
 * Validate billing address field
 */
export function validateAddressField(field: string, value: string): ValidationResult {
  const errors: string[] = [];

  const trimmed = value.trim();

  if (!trimmed) {
    errors.push(`${field} is required`);
    return { isValid: false, errors };
  }

  // Basic length check
  if (trimmed.length < 2) {
    errors.push(`${field} is too short (minimum 2 characters)`);
    return { isValid: false, errors };
  }

  if (trimmed.length > 100) {
    errors.push(`${field} is too long (maximum 100 characters)`);
    return { isValid: false, errors };
  }

  return { isValid: true, errors: [] };
}

/**
 * Comprehensive card validation
 * Validates all fields and returns detailed results
 */
export function validateCardData(data: {
  cardNumber: string;
  expiryDate: string;
  cvv: string;
  cardholderName: string;
  billingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
}): CardValidationResults {
  const cardNumber = validateCardNumberLuhn(data.cardNumber);
  const expiryDate = validateExpiryDate(data.expiryDate);
  const cvv = validateCVV(data.cvv);
  const cardholderName = validateCardholderName(data.cardholderName);

  const billingAddress = {
    street: validateAddressField("Street", data.billingAddress.street),
    city: validateAddressField("City", data.billingAddress.city),
    state: validateAddressField("State", data.billingAddress.state),
    zipCode: validateAddressField("Zip Code", data.billingAddress.zipCode),
    country: validateAddressField("Country", data.billingAddress.country),
  };

  // Overall validation: all fields must be valid
  const allFieldsValid =
    cardNumber.isValid &&
    expiryDate.isValid &&
    cvv.isValid &&
    cardholderName.isValid &&
    billingAddress.street.isValid &&
    billingAddress.city.isValid &&
    billingAddress.state.isValid &&
    billingAddress.zipCode.isValid &&
    billingAddress.country.isValid;

  const allErrors = [
    ...cardNumber.errors,
    ...expiryDate.errors,
    ...cvv.errors,
    ...cardholderName.errors,
    ...billingAddress.street.errors,
    ...billingAddress.city.errors,
    ...billingAddress.state.errors,
    ...billingAddress.zipCode.errors,
    ...billingAddress.country.errors,
  ];

  return {
    cardNumber,
    expiryDate,
    cvv,
    cardholderName,
    billingAddress,
    overall: {
      isValid: allFieldsValid,
      errors: allErrors,
    },
  };
}

/**
 * Mask card number for display
 * Shows only last 4 digits: **** **** **** 1234
 */
export function maskCardNumber(cardNumber: string): string {
  const cleaned = cardNumber.replace(/[\s-]/g, "");

  if (cleaned.length < 4) {
    return "*".repeat(cleaned.length);
  }

  const lastFour = cleaned.slice(-4);
  const masked = "*".repeat(cleaned.length - 4);

  // Format with spaces every 4 digits
  const parts = [];
  for (let i = 0; i < masked.length; i += 4) {
    parts.push(masked.slice(i, i + 4));
  }
  parts.push(lastFour);

  return parts.join(" ");
}
