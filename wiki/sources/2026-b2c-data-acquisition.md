---
type: source
title: "B2C Data Acquisition: How We Will Get Order and Chat History"
source_file: raw/assets/B2C_Data_Acquisition.docx
date_ingested: 2026-05-16
tags: [b2c, data-acquisition, ingestion, phase-0, shopify, whatsapp, stripe, no-scraping, urvee-organics]
---

# B2C Data Acquisition: How We Will Get Order and Chat History

**Source:** [[raw/assets/B2C_Data_Acquisition.docx]]
**Ingested:** 2026-05-16
**Type:** note
**Scope:** Phase 0 | B2C tenants

## Summary

For B2C tenants (e.g., [[entities/urvee-organics]]), public internet data is sparse, so the system relies entirely on the tenant's own customer interaction history. This document defines four acquisition methods in strict preference order: official APIs, webhooks, CSV upload, and — explicitly excluded — scraping.

The API-first approach covers the major commerce and communication platforms B2C tenants use: Shopify, WooCommerce, BigCommerce, and Magento for storefronts; WhatsApp Business API, Instagram Business Graph API, and Facebook Messenger Platform API for chat; Stripe and Razorpay for payment/transaction data. Marketplace APIs (Amazon Selling Partner, Flipkart Marketplace, Meesho Supplier) are deferred to Phase 1 and are restricted to the seller's own orders only — not full cross-platform customer history.

CSV upload is the universal fallback when no API exists, paired with an LLM-assisted column mapping step that auto-detects field roles (date, customer email, order value) and presents a one-click mapping confirmation to the tenant. Monthly reminders prompt tenants to re-upload and keep data fresh.

The no-scraping policy is a hard architectural boundary: automating logins to third-party marketplaces violates their Terms of Service, creates legal exposure, risks account suspension, and conflicts with GDPR. Where a tenant's data is locked inside a platform with no API or export path, the system accepts that data cannot be ingested.

## Key Claims

- Acquisition methods are in strict preference order: Official APIs → Webhooks → CSV upload → (Scraping excluded).
- Chat history is acquired via OAuth-based access to WhatsApp Business API, Instagram Business Graph API, and Facebook Messenger Platform API.
- Payment data is acquired via Stripe and Razorpay APIs; marketplace APIs (Phase 1) return seller-own-orders only.
- Webhooks serve tenants whose platforms support outbound push but lack a full pull API.
- CSV upload uses LLM to auto-map column headers to the internal schema; tenant confirms mapping in one click.
- Monthly re-upload reminders prevent data staleness.
- Scraping is explicitly prohibited — ToS violation, legal exposure, GDPR incompatibility, risk of account suspension.
- Behavioral signals derivable from own-ecosystem data (LTV, recency, frequency, category affinity, chat responsiveness) are stated as sufficient for accurate B2C scoring without cross-platform data.
- The data boundary is scoped to the tenant's own ecosystem; cross-retailer customer history is inaccessible by design.

## Entities Mentioned

- [[entities/urvee-organics]] — B2C POC tenant; this document directly defines how their customer history is acquired

## Concepts Mentioned

- [[concepts/b2c-data-acquisition]] — this document is the primary source for the 4-method strategy
- [[concepts/lead-ingestion-sources]] — B2C historical data acquisition is a prerequisite to lead scoring in Pipeline 1
- [[concepts/lead-pipeline-architecture]] — acquired data feeds Pipeline 1 (Event/Lead) as the raw input for enrichment and scoring

## Questions Raised

- Phase 1 marketplace APIs: what enrichment value do seller-own order records add vs. storefront order history from Shopify/WooCommerce? Are they worth the additional OAuth surface?
- LLM column-mapping for CSV: which model handles this step, and does it count against per-tenant LLM cost caps defined in [[analyses/client-config-schema-defaults]]?
- Monthly re-upload reminders: what triggers these (cron? last-ingest timestamp)? Is this a tenant notification or a pipeline event?
- Webhooks: do inbound webhook endpoints require a separate security model (signature verification, allowlisted IPs) beyond what Meta's webhooks already mandate?

## Quotes

> "We will not extract data by automating logins to third-party marketplaces. This violates the Terms of Service of Amazon, Flipkart, and Meesho; creates legal exposure; risks the tenant's account being suspended; and is incompatible with GDPR."

> "Behavioral signals derived from the tenant's own data — lifetime value, recency, frequency, category affinity, chat responsiveness — are sufficient to score B2C leads accurately."
