//! Search Analytics Module
//!
//! Tracks search queries and provides insights.

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::RwLock;

// ============================================================================
// Types
// ============================================================================

/// A recorded search query
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchRecord {
    /// Query text
    pub query: String,
    /// Number of results returned
    pub result_count: usize,
    /// Whether user clicked a result
    pub clicked: bool,
    /// Time to execute (ms)
    pub execution_time_ms: u64,
    /// Search type (semantic, keyword, hybrid)
    pub search_type: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
}

/// Query statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct QueryStats {
    /// Total times this query was searched
    pub count: u32,
    /// Total clicks on results
    pub clicks: u32,
    /// Average result count
    pub avg_results: f64,
    /// Average execution time
    pub avg_time_ms: f64,
    /// Last searched
    pub last_searched: Option<DateTime<Utc>>,
}

/// Search analytics summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsSummary {
    /// Total searches in period
    pub total_searches: u32,
    /// Searches with zero results
    pub zero_result_searches: u32,
    /// Click-through rate
    pub click_through_rate: f64,
    /// Average results per search
    pub avg_results_per_search: f64,
    /// Average execution time
    pub avg_execution_time_ms: f64,
    /// Top queries
    pub top_queries: Vec<(String, u32)>,
    /// Queries with no results
    pub failed_queries: Vec<String>,
    /// Period start
    pub period_start: DateTime<Utc>,
    /// Period end
    pub period_end: DateTime<Utc>,
}

// ============================================================================
// Search Analytics
// ============================================================================

/// Tracks and analyzes search behavior
pub struct SearchAnalytics {
    /// Individual search records
    records: RwLock<Vec<SearchRecord>>,
    /// Aggregated query stats
    query_stats: RwLock<HashMap<String, QueryStats>>,
    /// Maximum records to keep
    max_records: usize,
}

impl SearchAnalytics {
    pub fn new() -> Self {
        Self {
            records: RwLock::new(Vec::with_capacity(10000)),
            query_stats: RwLock::new(HashMap::new()),
            max_records: 100000,
        }
    }

    /// Record a search
    pub fn record(&self, record: SearchRecord) {
        let query_normalized = record.query.to_lowercase().trim().to_string();

        // Update aggregated stats
        {
            let mut stats = self.query_stats.write().unwrap();
            let entry = stats.entry(query_normalized).or_default();
            entry.count += 1;
            if record.clicked {
                entry.clicks += 1;
            }
            // Update rolling average
            let n = entry.count as f64;
            entry.avg_results = ((entry.avg_results * (n - 1.0)) + record.result_count as f64) / n;
            entry.avg_time_ms = ((entry.avg_time_ms * (n - 1.0)) + record.execution_time_ms as f64) / n;
            entry.last_searched = Some(record.timestamp);
        }

        // Store record
        {
            let mut records = self.records.write().unwrap();
            records.push(record);

            // Rotate if needed
            if records.len() > self.max_records {
                records.drain(0..10000);
            }
        }
    }

    /// Record a click on a search result
    pub fn record_click(&self, query: &str) {
        let query_normalized = query.to_lowercase().trim().to_string();

        let mut stats = self.query_stats.write().unwrap();
        if let Some(entry) = stats.get_mut(&query_normalized) {
            entry.clicks += 1;
        }
    }

    /// Get summary for a time period
    pub fn get_summary(&self, hours: i64) -> AnalyticsSummary {
        let cutoff = Utc::now() - Duration::hours(hours);
        let records = self.records.read().unwrap();

        let relevant: Vec<&SearchRecord> = records
            .iter()
            .filter(|r| r.timestamp > cutoff)
            .collect();

        let total_searches = relevant.len() as u32;
        let zero_result_searches = relevant.iter().filter(|r| r.result_count == 0).count() as u32;
        let clicks = relevant.iter().filter(|r| r.clicked).count();

        let click_through_rate = if total_searches > 0 {
            clicks as f64 / total_searches as f64
        } else {
            0.0
        };

        let avg_results_per_search = if total_searches > 0 {
            relevant.iter().map(|r| r.result_count).sum::<usize>() as f64 / total_searches as f64
        } else {
            0.0
        };

        let avg_execution_time_ms = if total_searches > 0 {
            relevant.iter().map(|r| r.execution_time_ms).sum::<u64>() as f64 / total_searches as f64
        } else {
            0.0
        };

        // Get top queries
        let stats = self.query_stats.read().unwrap();
        let mut query_counts: Vec<(&String, &QueryStats)> = stats.iter().collect();
        query_counts.sort_by(|a, b| b.1.count.cmp(&a.1.count));
        let top_queries: Vec<(String, u32)> = query_counts
            .iter()
            .take(10)
            .map(|(q, s)| ((*q).clone(), s.count))
            .collect();

        // Get failed queries
        let failed_queries: Vec<String> = relevant
            .iter()
            .filter(|r| r.result_count == 0)
            .map(|r| r.query.clone())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .take(20)
            .collect();

        AnalyticsSummary {
            total_searches,
            zero_result_searches,
            click_through_rate,
            avg_results_per_search,
            avg_execution_time_ms,
            top_queries,
            failed_queries,
            period_start: cutoff,
            period_end: Utc::now(),
        }
    }

    /// Get popular queries
    pub fn get_popular_queries(&self, limit: usize) -> Vec<(String, u32)> {
        let stats = self.query_stats.read().unwrap();
        let mut query_counts: Vec<(&String, &QueryStats)> = stats.iter().collect();
        query_counts.sort_by(|a, b| b.1.count.cmp(&a.1.count));

        query_counts
            .into_iter()
            .take(limit)
            .map(|(q, s)| (q.clone(), s.count))
            .collect()
    }

    /// Get queries with zero results
    pub fn get_zero_result_queries(&self, hours: i64) -> Vec<String> {
        let cutoff = Utc::now() - Duration::hours(hours);
        let records = self.records.read().unwrap();

        records
            .iter()
            .filter(|r| r.timestamp > cutoff && r.result_count == 0)
            .map(|r| r.query.clone())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect()
    }

    /// Get trending queries (most increase in recent period)
    pub fn get_trending_queries(&self, limit: usize) -> Vec<String> {
        let now = Utc::now();
        let recent_cutoff = now - Duration::hours(24);
        let older_cutoff = now - Duration::hours(168); // Last week

        let records = self.records.read().unwrap();

        // Count queries in recent vs older period
        let mut recent_counts: HashMap<String, u32> = HashMap::new();
        let mut older_counts: HashMap<String, u32> = HashMap::new();

        for record in records.iter() {
            let query = record.query.to_lowercase();
            if record.timestamp > recent_cutoff {
                *recent_counts.entry(query).or_default() += 1;
            } else if record.timestamp > older_cutoff {
                *older_counts.entry(query).or_default() += 1;
            }
        }

        // Calculate trend score (recent count / older count)
        let mut trends: Vec<(String, f64)> = recent_counts
            .into_iter()
            .map(|(q, recent)| {
                let older = *older_counts.get(&q).unwrap_or(&1) as f64;
                let score = (recent as f64) / (older / 7.0).max(1.0); // Normalize older period
                (q, score)
            })
            .collect();

        trends.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        trends.into_iter().take(limit).map(|(q, _)| q).collect()
    }

    /// Get stats for a specific query
    pub fn get_query_stats(&self, query: &str) -> Option<QueryStats> {
        let stats = self.query_stats.read().unwrap();
        let normalized = query.to_lowercase().trim().to_string();
        stats.get(&normalized).cloned()
    }

    /// Clear old records
    pub fn cleanup(&self, days: i64) {
        let cutoff = Utc::now() - Duration::days(days);
        let mut records = self.records.write().unwrap();
        records.retain(|r| r.timestamp > cutoff);
    }
}

impl Default for SearchAnalytics {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_search() {
        let analytics = SearchAnalytics::new();

        analytics.record(SearchRecord {
            query: "fireball damage".to_string(),
            result_count: 5,
            clicked: true,
            execution_time_ms: 50,
            search_type: "hybrid".to_string(),
            timestamp: Utc::now(),
        });

        let stats = analytics.get_query_stats("fireball damage").unwrap();
        assert_eq!(stats.count, 1);
        assert_eq!(stats.clicks, 1);
    }

    #[test]
    fn test_popular_queries() {
        let analytics = SearchAnalytics::new();

        for _ in 0..5 {
            analytics.record(SearchRecord {
                query: "popular query".to_string(),
                result_count: 3,
                clicked: false,
                execution_time_ms: 30,
                search_type: "hybrid".to_string(),
                timestamp: Utc::now(),
            });
        }

        analytics.record(SearchRecord {
            query: "rare query".to_string(),
            result_count: 1,
            clicked: false,
            execution_time_ms: 30,
            search_type: "hybrid".to_string(),
            timestamp: Utc::now(),
        });

        let popular = analytics.get_popular_queries(5);
        assert_eq!(popular[0].0, "popular query");
        assert_eq!(popular[0].1, 5);
    }

    #[test]
    fn test_summary() {
        let analytics = SearchAnalytics::new();

        analytics.record(SearchRecord {
            query: "test".to_string(),
            result_count: 5,
            clicked: true,
            execution_time_ms: 50,
            search_type: "hybrid".to_string(),
            timestamp: Utc::now(),
        });

        let summary = analytics.get_summary(24);
        assert_eq!(summary.total_searches, 1);
        assert!(summary.click_through_rate > 0.0);
    }
}
