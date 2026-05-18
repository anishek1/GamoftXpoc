---
type: concept
name: "B2C Data Acquisition"
aliases: ["B2C order history ingestion", "B2C chat history acquisition"]
tags: [b2c, data-acquisition, ingestion, phase-0, no-scraping, csv-upload, api-first]
source_count: 1
last_updated: 2026-05-16
confidence: high
---

# B2C Data Acquisition

## Definition

The strategy for acquiring B2C tenants' customer order history and chat history before and during lead processing. Because public internet data on B2C consumers is sparse, the system relies entirely on the **tenant's own ecosystem data** acquired through four methods in strict preference order.

## Four-Method Hierarchy

| Priority | Method | Scope |
|---|---|---|
| 1 | **Official APIs** | Shopify, WooCommerce, BigCommerce, Magento (stores); WhatsApp Business API, Instagram Business Graph API, Facebook Messenger Platform API (chat); Stripe, Razorpay (payments); Phase 1: Amazon Selling Partner API, Flipkart Marketplace API, Meesho Supplier API (marketplaces — seller-own-orders only) |
| 2 | **Webhooks** | Inbound push from custom checkout/chat systems with outbound webhook support but no full pull API |
| 3 | **CSV upload** | Manual export from any system; LLM-assisted column mapping; monthly re-upload reminders |
| 4 | **(Scraping — excluded)** | Explicitly prohibited. See No-Scraping Policy below. |

## Why It Matters

B2C lead scoring requires behavioral signal data — lifetime value, recency, frequency, category affinity, chat responsiveness — that does not exist in public databases. The only reliable source is the tenant's own transaction and conversation history. This document defines how that history flows into the system without crossing legal or platform ToS boundaries.

The data boundary is intentional: the system can aggregate a customer's full history **within the tenant's ecosystem** but cannot access purchases the customer made at other retailers or marketplaces. This limitation is framed in tenant-facing messaging as a known constraint, not a failure.

## Evidence & Examples

- Shopify/WooCommerce/BigCommerce/Magento via OAuth: pull complete order history (source: [[sources/2026-b2c-data-acquisition]])
- WhatsApp/Instagram/Messenger via Graph API: OAuth-based access to conversation history (source: [[sources/2026-b2c-data-acquisition]])
- Stripe/Razorpay: order and transaction data for tenants using these for checkout (source: [[sources/2026-b2c-data-acquisition]])
- Phase 1 marketplace APIs: seller-own orders only, not cross-marketplace customer history (source: [[sources/2026-b2c-data-acquisition]])

## LLM-Assisted CSV Column Mapping

The CSV upload path uses the LLM to auto-detect column roles (date, customer email, order value) and presents a one-click mapping confirmation. This is a one-time setup step — subsequent uploads use the saved mapping. Monthly reminders prompt tenants to re-upload.

**Open question:** Which model handles this step? Does it count against per-tenant LLM cost caps in [[analyses/client-config-schema-defaults]]?

## No-Scraping Policy

Scraping third-party marketplaces (automating logins to Amazon, Flipkart, Meesho) is explicitly prohibited on four grounds:
1. Violates the platform's Terms of Service
2. Creates legal exposure for both Gamoft and the tenant
3. Risks the tenant's marketplace seller account being suspended
4. Incompatible with GDPR

Where data is trapped in a platform with no API or export path, the system accepts data cannot be ingested and helps the tenant migrate if possible.

## Tensions & Contradictions

- Phase 1 marketplace APIs (Amazon Selling Partner, Flipkart, Meesho) are described as returning "only the seller's own orders, not full customer history across the marketplace." This raises the question of whether this enrichment is worth the OAuth integration surface area — the behavioral signals may be duplicative of what Shopify/WooCommerce already provide. (source: [[sources/2026-b2c-data-acquisition]])

## Related Concepts

- [[concepts/lead-ingestion-sources]] — the 4-source real-time ingestion strategy; B2C data acquisition is a prerequisite that backfills historical context
- [[concepts/lead-pipeline-architecture]] — acquired B2C data feeds Pipeline 1 enrichment and scoring
- [[concepts/signal-types]] — behavioral signals derivable from B2C data (LTV, recency, frequency, affinity, responsiveness) map to Engagement and Behaviour scoring dimensions

## Related Entities

- [[entities/urvee-organics]] — primary B2C POC tenant this strategy is designed for

## Sources

- [[sources/2026-b2c-data-acquisition]] — primary and only source for this concept
