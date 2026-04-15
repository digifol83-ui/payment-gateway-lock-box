import { z } from "zod";
import { publicProcedure, router } from "./_core/trpc";
import { parsePaymentInput, testClaudeConnection } from "./paymentParser";
import { validateCardData, maskCardNumber } from "./cardValidation";
import { createTransaction, getTransactionsByUserId, getTransactionCount } from "./paymentDb";
import type { ParsedPaymentData } from "./paymentParser";
import type { CardValidationResults } from "./cardValidation";

/**
 * Payment parsing and validation router
 * All procedures are public (no authentication required)
 */
export const paymentRouter = router({
  /**
   * Parse raw payment input using Claude AI
   */
  parsePayment: publicProcedure
    .input(
      z.object({
        rawInput: z.string().min(10, "Input must be at least 10 characters"),
        source: z.enum(["manual", "api", "pos"]).default("manual"),
      })
    )
    .mutation(async ({ input }) => {
      try {
        // Parse using Claude
        const parsed = await parsePaymentInput(input.rawInput);

        // Validate parsed data
        const validation = validateCardData({
          cardNumber: parsed.cardNumber,
          expiryDate: parsed.expiryDate,
          cvv: parsed.cvv,
          cardholderName: parsed.cardholderName,
          billingAddress: parsed.billingAddress,
        });

        // Mask card number for storage and display
        const maskedCard = maskCardNumber(parsed.cardNumber);

        // Create transaction record
        const transaction = await createTransaction({
          userId: null,
          rawInput: input.rawInput,
          maskedCardNumber: maskedCard,
          cardNumber: parsed.cardNumber, // Store for reference (in production, encrypt this)
          expiryDate: parsed.expiryDate,
          cvv: parsed.cvv,
          cardholderName: parsed.cardholderName,
          billingStreet: parsed.billingAddress.street,
          billingCity: parsed.billingAddress.city,
          billingState: parsed.billingAddress.state,
          billingZipCode: parsed.billingAddress.zipCode,
          billingCountry: parsed.billingAddress.country,
          validationStatus: validation.overall.isValid ? "valid" : "invalid",
          validationErrors: JSON.stringify(validation.overall.errors),
          confidenceScores: JSON.stringify(parsed.confidence),
          anomalies: JSON.stringify(parsed.anomalies),
          aiReasoning: parsed.rawAiReasoning,
          source: input.source,
        });

        return {
          success: true,
          transaction: transaction
            ? {
                id: transaction.id,
                maskedCardNumber: transaction.maskedCardNumber,
                createdAt: transaction.createdAt,
              }
            : null,
          parsed: {
            cardNumber: maskedCard,
            expiryDate: parsed.expiryDate,
            cvv: "***",
            cardholderName: parsed.cardholderName,
            billingAddress: parsed.billingAddress,
            confidence: parsed.confidence,
            anomalies: parsed.anomalies,
            rawAiReasoning: parsed.rawAiReasoning,
          },
          validation: {
            overall: validation.overall,
            cardNumber: validation.cardNumber,
            expiryDate: validation.expiryDate,
            cvv: validation.cvv,
            cardholderName: validation.cardholderName,
            billingAddress: validation.billingAddress,
          },
        };
      } catch (error) {
        console.error("Payment parsing error:", error);
        return {
          success: false,
          error: error instanceof Error ? error.message : "Failed to parse payment data",
        };
      }
    }),

  /**
   * Get transaction history
   */
  getTransactions: publicProcedure
    .input(
      z.object({
        limit: z.number().min(1).max(100).default(50),
        offset: z.number().min(0).default(0),
      })
    )
    .query(async ({ input }) => {
      try {
        const transactions = await getTransactionsByUserId(null, input.limit, input.offset);
        const total = await getTransactionCount(null);

        return {
          success: true,
          transactions: transactions.map((t) => ({
            id: t.id,
            maskedCardNumber: t.maskedCardNumber,
            cardholderName: t.cardholderName,
            validationStatus: t.validationStatus,
            source: t.source,
            createdAt: t.createdAt,
            confidence: t.confidenceScores ? JSON.parse(t.confidenceScores) : null,
            anomalies: t.anomalies ? JSON.parse(t.anomalies) : [],
          })),
          total,
          limit: input.limit,
          offset: input.offset,
        };
      } catch (error) {
        console.error("Get transactions error:", error);
        return {
          success: false,
          error: error instanceof Error ? error.message : "Failed to fetch transactions",
          transactions: [],
          total: 0,
        };
      }
    }),

  /**
   * Get transaction details by ID
   */
  getTransactionDetail: publicProcedure
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      try {
        const { getTransactionById } = await import("./paymentDb");
        const transaction = await getTransactionById(input.id);

        if (!transaction) {
          return {
            success: false,
            error: "Transaction not found",
          };
        }

        return {
          success: true,
          transaction: {
            id: transaction.id,
            rawInput: transaction.rawInput,
            maskedCardNumber: transaction.maskedCardNumber,
            cardholderName: transaction.cardholderName,
            expiryDate: transaction.expiryDate,
            billingAddress: {
              street: transaction.billingStreet,
              city: transaction.billingCity,
              state: transaction.billingState,
              zipCode: transaction.billingZipCode,
              country: transaction.billingCountry,
            },
            validationStatus: transaction.validationStatus,
            validationErrors: transaction.validationErrors ? JSON.parse(transaction.validationErrors) : [],
            confidenceScores: transaction.confidenceScores ? JSON.parse(transaction.confidenceScores) : null,
            anomalies: transaction.anomalies ? JSON.parse(transaction.anomalies) : [],
            aiReasoning: transaction.aiReasoning,
            source: transaction.source,
            createdAt: transaction.createdAt,
          },
        };
      } catch (error) {
        console.error("Get transaction detail error:", error);
        return {
          success: false,
          error: error instanceof Error ? error.message : "Failed to fetch transaction details",
        };
      }
    }),

  /**
   * Test Claude API connection
   */
  testConnection: publicProcedure.mutation(async () => {
    try {
      const isConnected = await testClaudeConnection();
      return {
        success: isConnected,
        message: isConnected ? "Claude API connection successful" : "Claude API connection failed",
      };
    } catch (error) {
      console.error("Connection test error:", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Connection test failed",
      };
    }
  }),

  /**
   * Validate card data without parsing
   */
  validateCard: publicProcedure
    .input(
      z.object({
        cardNumber: z.string(),
        expiryDate: z.string(),
        cvv: z.string(),
        cardholderName: z.string(),
        billingAddress: z.object({
          street: z.string(),
          city: z.string(),
          state: z.string(),
          zipCode: z.string(),
          country: z.string(),
        }),
      })
    )
    .mutation(async ({ input }) => {
      try {
        const validation = validateCardData(input);

        return {
          success: true,
          validation: {
            overall: validation.overall,
            cardNumber: validation.cardNumber,
            expiryDate: validation.expiryDate,
            cvv: validation.cvv,
            cardholderName: validation.cardholderName,
            billingAddress: validation.billingAddress,
          },
        };
      } catch (error) {
        console.error("Card validation error:", error);
        return {
          success: false,
          error: error instanceof Error ? error.message : "Validation failed",
        };
      }
    }),
});

export type PaymentRouter = typeof paymentRouter;
