# Lockbox — Payment Field Parsing & Validation Platform

## Architecture Overview
- **Frontend**: React 19 + Tailwind 4 (elegant, premium UI)
- **Backend**: Express 4 + tRPC 11 (type-safe API)
- **Database**: MySQL (transaction logging)
- **AI Engine**: Anthropic Claude API (payment field parsing)
- **Validation**: Luhn algorithm, date validation, CVV format checking

## Phase 1: Setup & Architecture
- [x] Create database schema for transactions, API keys, and validation results
- [x] Set up environment variables for Claude API key management
- [x] Create shared types for payment data structures
- [x] Initialize tRPC procedures for payment processing

## Phase 2: Backend Payment Parsing Engine
- [x] Implement Claude API integration with error handling
- [x] Create payment field extraction prompt engineering
- [x] Build raw input parsing procedure (accepts unstructured payment strings)
- [x] Implement field normalization and cleanup logic
- [x] Create test suite for parsing engine

## Phase 3: Card Validation Engine
- [x] Implement Luhn algorithm for card number validation
- [x] Build expiry date validation (format MM/YY and expiration check)
- [x] Build CVV format validation (3-4 digits)
- [x] Build cardholder name validation (required, non-empty)
- [x] Build billing address validation (required fields)
- [x] Create comprehensive validation result structure with per-field errors
- [x] Write unit tests for all validation functions

## Phase 4: Database & Transaction Logging
- [x] Create transactions table schema (timestamp, source, masked_card, parsed_fields, validation_status, ai_reasoning)
- [x] Implement transaction creation procedure
- [x] Implement transaction retrieval and filtering
- [x] Build transaction history query with pagination
- [x] Write migration SQL

## Phase 5: API Key Management
- [x] Create API key storage and encryption in database
- [x] Build secure API key input and save procedure
- [x] Implement test connection endpoint (verify Claude API key validity)
- [x] Create API key retrieval (masked for display)
- [x] Build API key update/refresh logic

## Phase 6: Frontend Dashboard Layout
- [x] Design elegant, premium Lockbox dashboard shell
- [x] Implement responsive grid layout with panels
- [x] Create navigation between API Config, Payment Parser, and Transaction Log
- [x] Build premium color scheme and typography
- [x] Implement loading states and error boundaries
- [x] Create empty states for transaction log

## Phase 7: API Key Configuration Panel
- [x] Build API key input field with secure masking
- [x] Implement "Save API Key" button with success feedback
- [x] Build "Test Connection" button with live validation
- [x] Display connection status indicator (connected/disconnected/error)
- [x] Show error messages for invalid keys
- [x] Add loading spinner during test

## Phase 8: Payment Input Form
- [x] Create form with separate fields: card number, expiry date, CVV, cardholder name, billing address
- [x] Implement real-time field formatting (card number spacing, expiry MM/YY)
- [x] Build form submission to Claude parser
- [x] Display loading state during AI parsing
- [x] Show parsing results with field breakdown

## Phase 9: AI Analysis Panel
- [x] Display Claude's parsed output for each field
- [x] Show confidence scores or field extraction notes
- [x] Display any anomaly flags or warnings from Claude
- [x] Show raw AI reasoning/explanation
- [x] Implement collapsible sections for detailed analysis

## Phase 10: Card Validation Display
- [x] Show validation results per field (pass/fail)
- [x] Display detailed error messages for failed validations
- [x] Implement visual indicators (checkmarks, error icons)
- [x] Show overall transaction validation status
- [x] Build status badge (Valid/Invalid/Needs Review)

## Phase 11: Transaction Log Dashboard
- [x] Display table of all parsed transactions
- [x] Show columns: timestamp, source, masked card number, parsed fields summary, validation status
- [x] Implement masked card number display (e.g., **** **** **** 1234)
- [x] Add sorting and filtering by status/date
- [x] Implement pagination for large transaction lists
- [x] Build transaction detail view (expandable rows)
- [ ] Add export/download transaction log feature

## Phase 12: Masked Card Display Utility
- [x] Create maskCardNumber(cardNumber) utility function
- [x] Ensure all card displays use masked format throughout app
- [x] Test masking on dashboard, logs, and detail views
- [x] Verify no unmasked card numbers appear anywhere

## Phase 13: Premium UI Polish
- [x] Implement smooth transitions and micro-interactions
- [x] Add refined shadows and spacing
- [x] Create consistent button and input styling
- [x] Build premium form styling with focus states
- [x] Implement elegant empty states
- [ ] Add loading skeletons for better perceived performance
- [x] Ensure perfect typography and visual hierarchy

## Phase 14: Testing & Validation
- [ ] Write vitest tests for Luhn algorithm
- [ ] Write vitest tests for date validation
- [ ] Write vitest tests for CVV validation
- [ ] Write vitest tests for Claude API integration
- [ ] Write vitest tests for payment parsing procedure
- [ ] Write vitest tests for transaction logging
- [ ] Write vitest tests for API key management
- [ ] Test end-to-end flow: input → parse → validate → log

## Phase 15: Security & Hardening
- [ ] Ensure Claude API key is never logged or exposed
- [ ] Verify card numbers are never stored unmasked
- [ ] Implement rate limiting on parsing endpoint
- [ ] Add CSRF protection
- [ ] Verify session security
- [ ] Test for XSS vulnerabilities

## Phase 16: Final Delivery
- [ ] Create checkpoint
- [ ] Verify all features working end-to-end
- [ ] Test on multiple browsers
- [ ] Confirm elegant, premium UI appearance
- [ ] Document API key setup instructions
- [ ] Deliver to user with usage guide


## Bug Fixes
- [ ] Fix 404 error on route /?from_webdev=1 - Home page redirect breaking query parameters
