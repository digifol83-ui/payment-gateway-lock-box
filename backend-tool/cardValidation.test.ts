import { describe, it, expect } from "vitest";
import {
  validateCardNumberLuhn,
  validateExpiryDate,
  validateCVV,
  validateCardholderName,
  validateAddressField,
  validateCardData,
  maskCardNumber,
} from "./cardValidation";

describe("Card Validation", () => {
  describe("validateCardNumberLuhn", () => {
    it("should validate a correct card number", () => {
      // Valid test card number (Visa)
      const result = validateCardNumberLuhn("4532015112830366");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject invalid card number", () => {
      const result = validateCardNumberLuhn("4532015112830367");
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it("should handle spaces and dashes", () => {
      const result = validateCardNumberLuhn("4532 0151 1283 0366");
      expect(result.isValid).toBe(true);
    });

    it("should reject non-numeric characters", () => {
      const result = validateCardNumberLuhn("453a-0151-1283-0366");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("only digits");
    });

    it("should reject too short card number", () => {
      const result = validateCardNumberLuhn("1234");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("between 13 and 19");
    });

    it("should reject too long card number", () => {
      const result = validateCardNumberLuhn("12345678901234567890");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("between 13 and 19");
    });
  });

  describe("validateExpiryDate", () => {
    it("should validate correct future expiry date", () => {
      // Use a future date
      const futureYear = ((new Date().getFullYear() % 100) + 5).toString().padStart(2, "0");
      const result = validateExpiryDate(`12/${futureYear}`);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject invalid month", () => {
      const futureYear = ((new Date().getFullYear() % 100) + 1).toString().padStart(2, "0");
      const result = validateExpiryDate(`13/${futureYear}`);
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("Invalid month");
    });

    it("should reject invalid format", () => {
      const result = validateExpiryDate("12-25");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("MM/YY format");
    });

    it("should reject expired date", () => {
      const pastYear = ((new Date().getFullYear() % 100) - 1).toString().padStart(2, "0");
      const result = validateExpiryDate(`01/${pastYear}`);
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("expired");
    });

    it("should reject current month if already passed", () => {
      const now = new Date();
      const currentMonth = (now.getMonth()).toString().padStart(2, "0"); // Previous month
      const currentYear = (now.getFullYear() % 100).toString().padStart(2, "0");

      if (now.getMonth() > 0) {
        const result = validateExpiryDate(`${currentMonth}/${currentYear}`);
        expect(result.isValid).toBe(false);
      }
    });
  });

  describe("validateCVV", () => {
    it("should validate correct 3-digit CVV", () => {
      const result = validateCVV("123");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate correct 4-digit CVV", () => {
      const result = validateCVV("1234");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject too short CVV", () => {
      const result = validateCVV("12");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("3-4 digits");
    });

    it("should reject too long CVV", () => {
      const result = validateCVV("12345");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("3-4 digits");
    });

    it("should reject non-numeric CVV", () => {
      const result = validateCVV("12a");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("only digits");
    });

    it("should handle spaces", () => {
      const result = validateCVV("1 2 3");
      expect(result.isValid).toBe(true);
    });
  });

  describe("validateCardholderName", () => {
    it("should validate correct name with first and last", () => {
      const result = validateCardholderName("John Doe");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate name with middle initial", () => {
      const result = validateCardholderName("John M Doe");
      expect(result.isValid).toBe(true);
    });

    it("should validate name with hyphen", () => {
      const result = validateCardholderName("Mary-Jane Smith");
      expect(result.isValid).toBe(true);
    });

    it("should validate name with apostrophe", () => {
      const result = validateCardholderName("O'Brien Smith");
      expect(result.isValid).toBe(true);
    });

    it("should reject empty name", () => {
      const result = validateCardholderName("");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("required");
    });

    it("should reject single name", () => {
      const result = validateCardholderName("John");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("first and last name");
    });

    it("should reject name with invalid characters", () => {
      const result = validateCardholderName("John@Doe");
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it("should reject name with numbers", () => {
      const result = validateCardholderName("John123 Doe");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("invalid characters");
    });
  });

  describe("validateAddressField", () => {
    it("should validate correct address field", () => {
      const result = validateAddressField("Street", "123 Main Street");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject empty field", () => {
      const result = validateAddressField("City", "");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("required");
    });

    it("should reject too short field", () => {
      const result = validateAddressField("State", "A");
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("too short");
    });

    it("should reject too long field", () => {
      const longString = "A".repeat(101);
      const result = validateAddressField("Street", longString);
      expect(result.isValid).toBe(false);
      expect(result.errors[0]).toContain("too long");
    });
  });

  describe("validateCardData", () => {
    it("should validate complete valid card data", () => {
      const futureYear = ((new Date().getFullYear() % 100) + 5).toString().padStart(2, "0");
      const result = validateCardData({
        cardNumber: "4532015112830366",
        expiryDate: `12/${futureYear}`,
        cvv: "123",
        cardholderName: "John Doe",
        billingAddress: {
          street: "123 Main Street",
          city: "New York",
          state: "NY",
          zipCode: "10001",
          country: "USA",
        },
      });

      expect(result.overall.isValid).toBe(true);
      expect(result.cardNumber.isValid).toBe(true);
      expect(result.expiryDate.isValid).toBe(true);
      expect(result.cvv.isValid).toBe(true);
      expect(result.cardholderName.isValid).toBe(true);
      expect(result.billingAddress.street.isValid).toBe(true);
    });

    it("should fail if any field is invalid", () => {
      const futureYear = ((new Date().getFullYear() % 100) + 5).toString().padStart(2, "0");
      const result = validateCardData({
        cardNumber: "4532015112830367", // Invalid
        expiryDate: `12/${futureYear}`,
        cvv: "123",
        cardholderName: "John Doe",
        billingAddress: {
          street: "123 Main Street",
          city: "New York",
          state: "NY",
          zipCode: "10001",
          country: "USA",
        },
      });

      expect(result.overall.isValid).toBe(false);
      expect(result.cardNumber.isValid).toBe(false);
    });
  });

  describe("maskCardNumber", () => {
    it("should mask card number showing only last 4 digits", () => {
      const masked = maskCardNumber("4532015112830366");
      expect(masked).toBe("**** **** **** 0366");
    });

    it("should handle card numbers with spaces", () => {
      const masked = maskCardNumber("4532 0151 1283 0366");
      expect(masked).toBe("**** **** **** 0366");
    });

    it("should handle card numbers with dashes", () => {
      const masked = maskCardNumber("4532-0151-1283-0366");
      expect(masked).toBe("**** **** **** 0366");
    });

    it("should handle short card numbers", () => {
      const masked = maskCardNumber("123");
      expect(masked).toBe("***");
    });

    it("should format with spaces every 4 digits", () => {
      const masked = maskCardNumber("378282246310005");
      expect(masked).toContain("0005");
      expect(masked.split(" ").length).toBeGreaterThan(1);
    });
  });
});
