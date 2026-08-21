"""Application services.

Services orchestrate use cases. They receive provider bundles and must not
import a concrete vendor adapter. Portfolio ingestion uses the persistence
store, not market-data providers. Stock Analyzer retrieval uses injected
market and fundamental contracts and never reads an uploaded portfolio.
Watchlist monitoring stores selected symbols and reuses Stock Analyzer
retrieval for current quotes; it does not run AI analysis. The Dashboard
overview reads live index quotes and, when a portfolio exists, compact
valuation and risk labels without running the analysis workflow. Analysis
invokes the compiled workflow and maps a public result.
"""
