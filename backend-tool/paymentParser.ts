import { invokeLLM } from "./_core/llm";
import type { TextContent } from "./_core/llm";

/**
 * Structured payment data extracted from raw input
 */

export interface BillingAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

export interface ConfidenceScores {
  cardNumber: number;
  expiryDate: number;
  cvv: number;
  cardholderName: number;
  billingAddress: number;
}

export interface ParsedPaymentData {
  cardNumber: string;
  expiryDate: string; // MM/YY format
  cvv: string;
  cardholderName: string;
  billingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  confidence: {
    cardNumber: number; // 0-1
    expiryDate: number;
    cvv: number;
    cardholderName: number;
    billingAddress: number;
  };
  anomalies: string[];
  rawAiReasoning: string;
}

/**
 * Parse raw payment input string using Claude AI
 * Extracts and structures payment fields from unstructured text
 */
export async function parsePaymentInput(rawInput: string): Promise<ParsedPaymentData> {
  const systemPrompt = `You are an expert payment data parser. Your task is to extract payment information from raw, unstructured input strings.

You must extract the following fields:
- Card Number (16 digits, may be formatted with spaces or dashes)
- Expiry Date (MM/YY format)
- CVV (3-4 digits)
- Cardholder Name
- Billing Address (street, city, state, zip code, country)

Return a JSON response with this exact structure:
{
  "cardNumber": "extracted card number without formatting",
  "expiryDate": "MM/YY format",
  "cvv": "3-4 digits",
  "cardholderName": "full name",
  "billingAddress": {
    "street": "street address",
    "city": "city",
    "state": "state/province",
    "zipCode": "postal code",
    "country": "country"
  },
  "confidence": {
    "cardNumber": 0.95,
    "expiryDate": 0.90,
    "cvv": 0.85,
    "cardholderName": 0.98,
    "billingAddress": 0.88
  },
  "anomalies": ["list of any suspicious patterns or missing data"]
}

Confidence scores should reflect how certain you are about each extraction (0.0 to 1.0).
If a field is missing or unclear, set confidence to 0 and include in anomalies.
Be strict about data quality - if something doesn't look right, flag it.`;

  const userPrompt = `Parse this payment input and extract all fields:\n\n${rawInput}`;

  try {
    const response = await invokeLLM({
      messages: [
        { role: "system", content: systemPrompt as string },
        { role: "user", content: userPrompt as string },
      ],
      response_format: {
        type: "json_schema",
        json_schema: {
          name: "payment_data",
          strict: true,
          schema: {
            type: "object",
            properties: {
              cardNumber: { type: "string" },
              expiryDate: { type: "string" },
              cvv: { type: "string" },
              cardholderName: { type: "string" },
              billingAddress: {
                type: "object",
                properties: {
                  street: { type: "string" },
                  city: { type: "string" },
                  state: { type: "string" },
                  zipCode: { type: "string" },
                  country: { type: "string" },
                },
                required: ["street", "city", "state", "zipCode", "country"],
                additionalProperties: false,
              },
              confidence: {
                type: "object",
                properties: {
                  cardNumber: { type: "number" },
                  expiryDate: { type: "number" },
                  cvv: { type: "number" },
                  cardholderName: { type: "number" },
                  billingAddress: { type: "number" },
                },
                required: ["cardNumber", "expiryDate", "cvv", "cardholderName", "billingAddress"],
                additionalProperties: false,
              },
              anomalies: {
                type: "array",
                items: { type: "string" },
              },
            },
            required: ["cardNumber", "expiryDate", "cvv", "cardholderName", "billingAddress", "confidence", "anomalies"],
            additionalProperties: false,
          },
        },
      },
    });

    const content = response.choices[0]?.message.content;
    if (!content) {
      throw new Error("No response from Claude API");
    }

    // Handle both string and array content types
    let jsonString: string;
    if (typeof content === "string") {
      jsonString = content;
    } else if (Array.isArray(content)) {
      // Extract text from content array
      jsonString = content
        .filter((c): c is { type: "text"; text: string } => c.type === "text")
        .map((c) => c.text)
        .join("\n");
    } else {
      throw new Error("Unexpected response content format");
    }

    const parsed = JSON.parse(jsonString);

    return {
      ...parsed,
      rawAiReasoning: `Parsed using Claude with confidence scores: Card ${parsed.confidence.cardNumber}, Expiry ${parsed.confidence.expiryDate}, CVV ${parsed.confidence.cvv}, Name ${parsed.confidence.cardholderName}, Address ${parsed.confidence.billingAddress}`,
    };
  } catch (error) {
    console.error("Payment parsing error:", error);
    throw new Error(`Failed to parse payment data: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

/**
 * Test Claude API connection
 * Returns true if API key is valid and service is reachable
 */
export async function testClaudeConnection(): Promise<boolean> {
  try {
    const response = await invokeLLM({
      messages: [
        {
          role: "user",
          content: "Respond with a single word: 'connected'" as string,
        },
      ],
    });

    const content = response.choices[0]?.message.content;
    const isValid = typeof content === "string" ? content.length > 0 : Array.isArray(content) && content.length > 0;
    return isValid;
  } catch (error) {
    console.error("Claude connection test failed:", error);
    return false;
  }
}
