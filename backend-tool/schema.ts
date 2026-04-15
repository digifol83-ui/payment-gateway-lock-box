import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * API Keys table for storing Claude API keys
 */
export const apiKeys = mysqlTable("apiKeys", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  encryptedKey: text("encryptedKey").notNull(),
  keyHash: varchar("keyHash", { length: 64 }).notNull().unique(),
  isActive: int("isActive").default(1).notNull(),
  lastTestedAt: timestamp("lastTestedAt"),
  lastTestSuccess: int("lastTestSuccess"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type ApiKey = typeof apiKeys.$inferSelect;
export type InsertApiKey = typeof apiKeys.$inferInsert;

/**
 * Transactions table for logging all parsed payment data
 */
export const transactions = mysqlTable("transactions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  rawInput: text("rawInput").notNull(),
  maskedCardNumber: varchar("maskedCardNumber", { length: 32 }).notNull(),
  cardNumber: varchar("cardNumber", { length: 32 }).notNull(),
  expiryDate: varchar("expiryDate", { length: 10 }).notNull(),
  cvv: varchar("cvv", { length: 4 }).notNull(),
  cardholderName: varchar("cardholderName", { length: 100 }).notNull(),
  billingStreet: varchar("billingStreet", { length: 255 }).notNull(),
  billingCity: varchar("billingCity", { length: 100 }).notNull(),
  billingState: varchar("billingState", { length: 100 }).notNull(),
  billingZipCode: varchar("billingZipCode", { length: 20 }).notNull(),
  billingCountry: varchar("billingCountry", { length: 100 }).notNull(),
  validationStatus: mysqlEnum("validationStatus", ["valid", "invalid", "pending"]).default("pending").notNull(),
  validationErrors: text("validationErrors"),
  confidenceScores: text("confidenceScores"),
  anomalies: text("anomalies"),
  aiReasoning: text("aiReasoning"),
  source: varchar("source", { length: 50 }).default("manual").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Transaction = typeof transactions.$inferSelect;
export type InsertTransaction = typeof transactions.$inferInsert;