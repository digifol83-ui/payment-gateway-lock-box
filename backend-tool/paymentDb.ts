import { eq } from "drizzle-orm";
import { apiKeys, transactions, type InsertTransaction, type Transaction } from "../drizzle/schema";
import { getDb } from "./db";

/**
 * Create a new transaction record
 */
export async function createTransaction(data: InsertTransaction): Promise<Transaction | null> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot create transaction: database not available");
    return null;
  }

  try {
    const result = await db.insert(transactions).values(data);
    if (result[0]?.insertId) {
      const created = await db
        .select()
        .from(transactions)
        .where(eq(transactions.id, Number(result[0].insertId)))
        .limit(1);
      return created[0] || null;
    }
    return null;
  } catch (error) {
    console.error("[Database] Failed to create transaction:", error);
    throw error;
  }
}

/**
 * Get transaction by ID
 */
export async function getTransactionById(id: number): Promise<Transaction | null> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get transaction: database not available");
    return null;
  }

  try {
    const result = await db.select().from(transactions).where(eq(transactions.id, id)).limit(1);
    return result[0] || null;
  } catch (error) {
    console.error("[Database] Failed to get transaction:", error);
    throw error;
  }
}

/**
 * Get all transactions for a user, ordered by most recent
 */
export async function getTransactionsByUserId(
  userId: number | null,
  limit: number = 50,
  offset: number = 0
): Promise<Transaction[]> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get transactions: database not available");
    return [];
  }

  try {
    if (userId !== null) {
      const results = await db
        .select()
        .from(transactions)
        .where(eq(transactions.userId, userId))
        .orderBy((t) => t.createdAt)
        .limit(limit)
        .offset(offset);
      return results;
    } else {
      const results = await db
        .select()
        .from(transactions)
        .orderBy((t) => t.createdAt)
        .limit(limit)
        .offset(offset);
      return results;
    }
  } catch (error) {
    console.error("[Database] Failed to get transactions:", error);
    throw error;
  }
}

/**
 * Get transaction count for pagination
 */
export async function getTransactionCount(userId: number | null = null): Promise<number> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot count transactions: database not available");
    return 0;
  }

  try {
    if (userId !== null) {
      const results = await db
        .select()
        .from(transactions)
        .where(eq(transactions.userId, userId));
      return results.length;
    } else {
      const results = await db.select().from(transactions);
      return results.length;
    }
  } catch (error) {
    console.error("[Database] Failed to count transactions:", error);
    throw error;
  }
}

/**
 * Save or update API key for a user
 */
export async function saveApiKey(
  userId: number | null,
  encryptedKey: string,
  keyHash: string
): Promise<boolean> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot save API key: database not available");
    return false;
  }

  try {
    // Check if key already exists
    const existing = await db.select().from(apiKeys).where(eq(apiKeys.keyHash, keyHash)).limit(1);

    if (existing.length > 0) {
      // Update existing
      await db
        .update(apiKeys)
        .set({
          encryptedKey,
          isActive: 1,
          updatedAt: new Date(),
        })
        .where(eq(apiKeys.keyHash, keyHash));
    } else {
      // Insert new
      await db.insert(apiKeys).values({
        userId,
        encryptedKey,
        keyHash,
        isActive: 1,
      });
    }

    return true;
  } catch (error) {
    console.error("[Database] Failed to save API key:", error);
    throw error;
  }
}

/**
 * Get API key for a user
 */
export async function getApiKeyByUserId(userId: number | null): Promise<string | null> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get API key: database not available");
    return null;
  }

  try {
    if (userId !== null) {
      const results = await db
        .select()
        .from(apiKeys)
        .where(eq(apiKeys.isActive, 1))
        .limit(1);
      return results[0]?.encryptedKey || null;
    } else {
      const results = await db
        .select()
        .from(apiKeys)
        .where(eq(apiKeys.isActive, 1))
        .limit(1);
      return results[0]?.encryptedKey || null;
    }
  } catch (error) {
    console.error("[Database] Failed to get API key:", error);
    throw error;
  }
}

/**
 * Update API key test result
 */
export async function updateApiKeyTestResult(keyHash: string, success: boolean): Promise<boolean> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot update API key test: database not available");
    return false;
  }

  try {
    await db
      .update(apiKeys)
      .set({
        lastTestedAt: new Date(),
        lastTestSuccess: success ? 1 : 0,
      })
      .where(eq(apiKeys.keyHash, keyHash));

    return true;
  } catch (error) {
    console.error("[Database] Failed to update API key test:", error);
    throw error;
  }
}
