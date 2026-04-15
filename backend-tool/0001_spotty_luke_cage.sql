CREATE TABLE `apiKeys` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`encryptedKey` text NOT NULL,
	`keyHash` varchar(64) NOT NULL,
	`isActive` int NOT NULL DEFAULT 1,
	`lastTestedAt` timestamp,
	`lastTestSuccess` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `apiKeys_id` PRIMARY KEY(`id`),
	CONSTRAINT `apiKeys_keyHash_unique` UNIQUE(`keyHash`)
);
--> statement-breakpoint
CREATE TABLE `transactions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`rawInput` text NOT NULL,
	`maskedCardNumber` varchar(32) NOT NULL,
	`cardNumber` varchar(32) NOT NULL,
	`expiryDate` varchar(10) NOT NULL,
	`cvv` varchar(4) NOT NULL,
	`cardholderName` varchar(100) NOT NULL,
	`billingStreet` varchar(255) NOT NULL,
	`billingCity` varchar(100) NOT NULL,
	`billingState` varchar(100) NOT NULL,
	`billingZipCode` varchar(20) NOT NULL,
	`billingCountry` varchar(100) NOT NULL,
	`validationStatus` enum('valid','invalid','pending') NOT NULL DEFAULT 'pending',
	`validationErrors` text,
	`confidenceScores` text,
	`anomalies` text,
	`aiReasoning` text,
	`source` varchar(50) NOT NULL DEFAULT 'manual',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `transactions_id` PRIMARY KEY(`id`)
);
