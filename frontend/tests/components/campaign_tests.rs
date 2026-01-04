//! Campaign Component Tests
//!
//! Tests for CampaignDashboard, CampaignCard, and campaign selection state.

use wasm_bindgen_test::*;
use leptos::prelude::*;
use ttrpg_assistant_frontend::components::campaign::campaign_card::{CampaignCard, CampaignGenre, CampaignCardCompact};
use ttrpg_assistant_frontend::components::campaign::campaign_dashboard::DashboardTab;
use ttrpg_assistant_frontend::bindings::{Campaign, CampaignSettings};
use ttrpg_assistant_frontend::services::layout_service::provide_layout_state;
use leptos_router::components::Router;

/// Helper function to create a test campaign with default settings
fn create_test_campaign(id: &str, name: &str, system: &str, description: Option<&str>) -> Campaign {
    Campaign {
        id: id.to_string(),
        name: name.to_string(),
        system: system.to_string(),
        description: description.map(|s| s.to_string()),
        created_at: "2024-01-01T00:00:00Z".to_string(),
        updated_at: "2024-01-01T00:00:00Z".to_string(),
        settings: CampaignSettings::default(),
    }
}

wasm_bindgen_test_configure!(run_in_browser);

// ============================================================================
// CampaignGenre Tests
// ============================================================================

#[wasm_bindgen_test]
fn test_campaign_genre_from_system_fantasy() {
    // Use pattern matching since CampaignGenre doesn't implement Debug
    assert!(matches!(CampaignGenre::from_system("D&D 5e"), CampaignGenre::Fantasy));
    assert!(matches!(CampaignGenre::from_system("Pathfinder 2e"), CampaignGenre::Fantasy));
    assert!(matches!(CampaignGenre::from_system("5E"), CampaignGenre::Fantasy));
    assert!(matches!(CampaignGenre::from_system("Warhammer Fantasy"), CampaignGenre::Fantasy));
}

#[wasm_bindgen_test]
fn test_campaign_genre_from_system_horror() {
    assert!(matches!(CampaignGenre::from_system("Call of Cthulhu"), CampaignGenre::Horror));
    assert!(matches!(CampaignGenre::from_system("Vampire: The Masquerade"), CampaignGenre::Horror));
    assert!(matches!(CampaignGenre::from_system("Delta Green"), CampaignGenre::Horror));
    assert!(matches!(CampaignGenre::from_system("Kult"), CampaignGenre::Horror));
    assert!(matches!(CampaignGenre::from_system("Vaesen"), CampaignGenre::Horror));
}

#[wasm_bindgen_test]
fn test_campaign_genre_from_system_cyberpunk() {
    assert!(matches!(CampaignGenre::from_system("Cyberpunk Red"), CampaignGenre::Cyberpunk));
    assert!(matches!(CampaignGenre::from_system("Shadowrun"), CampaignGenre::Cyberpunk));
    assert!(matches!(CampaignGenre::from_system("The Sprawl"), CampaignGenre::Cyberpunk));
    assert!(matches!(CampaignGenre::from_system("Neon City"), CampaignGenre::Cyberpunk));
}

#[wasm_bindgen_test]
fn test_campaign_genre_from_system_scifi() {
    assert!(matches!(CampaignGenre::from_system("Traveller"), CampaignGenre::SciFi));
    assert!(matches!(CampaignGenre::from_system("Mothership"), CampaignGenre::SciFi));
    assert!(matches!(CampaignGenre::from_system("Stars Without Number"), CampaignGenre::SciFi));
    assert!(matches!(CampaignGenre::from_system("Alien RPG"), CampaignGenre::SciFi));
    assert!(matches!(CampaignGenre::from_system("Space Opera"), CampaignGenre::SciFi));
}

#[wasm_bindgen_test]
fn test_campaign_genre_from_system_unknown() {
    assert!(matches!(CampaignGenre::from_system(""), CampaignGenre::Unknown));
    assert!(matches!(CampaignGenre::from_system("Custom System"), CampaignGenre::Unknown));
    assert!(matches!(CampaignGenre::from_system("My Homebrew"), CampaignGenre::Unknown));
}

#[wasm_bindgen_test]
fn test_campaign_genre_style_returns_tuple() {
    let (bg_class, text_class) = CampaignGenre::Fantasy.style();
    assert!(bg_class.contains("gradient"));
    assert!(bg_class.contains("amber"));
    assert!(text_class.contains("amber"));
}

#[wasm_bindgen_test]
fn test_campaign_genre_label() {
    // Test labels via direct string comparison
    assert_eq!(CampaignGenre::Fantasy.label(), "Fantasy");
    assert_eq!(CampaignGenre::Horror.label(), "Horror");
    assert_eq!(CampaignGenre::Cyberpunk.label(), "Cyberpunk");
    assert_eq!(CampaignGenre::SciFi.label(), "Sci-Fi");
    assert_eq!(CampaignGenre::Modern.label(), "Modern");
    assert_eq!(CampaignGenre::Historical.label(), "Historical");
    assert_eq!(CampaignGenre::Unknown.label(), "RPG");
}

// ============================================================================
// DashboardTab Tests
// ============================================================================

#[wasm_bindgen_test]
fn test_dashboard_tab_default() {
    // Test that default creates Overview tab using pattern matching
    let tab = DashboardTab::default();
    assert!(matches!(tab, DashboardTab::Overview));
}

#[wasm_bindgen_test]
fn test_dashboard_tab_equality() {
    // Test equality using the derived PartialEq
    let tab1 = DashboardTab::Overview;
    let tab2 = DashboardTab::Overview;
    let tab3 = DashboardTab::Entities;

    assert!(tab1 == tab2);
    assert!(tab1 != tab3);
}

#[wasm_bindgen_test]
fn test_dashboard_tab_variants_exist() {
    // Test that all expected variants exist
    let _overview = DashboardTab::Overview;
    let _entities = DashboardTab::Entities;
    let _world_state = DashboardTab::WorldState;
    let _versions = DashboardTab::Versions;
    let _relationships = DashboardTab::Relationships;
    // If this compiles, all variants exist
}

// ============================================================================
// CampaignCard Component Tests
// ============================================================================

#[wasm_bindgen_test]
fn test_campaign_card_renders_without_panic() {
    // This test ensures the CampaignCard component can be mounted without panicking
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "test-id-123",
            "Test Campaign",
            "D&D 5e",
            Some("A test campaign description"),
        );

        let on_click = Callback::new(|_id: String| {
            // Click handler - do nothing in test
        });

        view! {
            <Router>
                <CampaignCard
                    campaign=campaign
                    on_click=on_click
                />
            </Router>
        }
    });
}

#[wasm_bindgen_test]
fn test_campaign_card_with_session_count() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "test-id-456",
            "Sessions Campaign",
            "Pathfinder 2e",
            None,
        );

        let on_click = Callback::new(|_id: String| {});

        view! {
            <Router>
                <CampaignCard
                    campaign=campaign
                    session_count=42
                    on_click=on_click
                />
            </Router>
        }
    });
}

#[wasm_bindgen_test]
fn test_campaign_card_active_state() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "active-campaign",
            "Active Campaign",
            "Call of Cthulhu",
            Some("Currently playing"),
        );

        let on_click = Callback::new(|_id: String| {});

        view! {
            <Router>
                <CampaignCard
                    campaign=campaign
                    is_active=true
                    on_click=on_click
                />
            </Router>
        }
    });
}

#[wasm_bindgen_test]
fn test_campaign_card_selected_state() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "selected-campaign",
            "Selected Campaign",
            "Cyberpunk Red",
            None,
        );

        let on_click = Callback::new(|_id: String| {});

        view! {
            <Router>
                <CampaignCard
                    campaign=campaign
                    is_selected=true
                    on_click=on_click
                />
            </Router>
        }
    });
}

#[wasm_bindgen_test]
fn test_campaign_card_with_delete_handler() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "deletable-campaign",
            "Deletable Campaign",
            "Mothership",
            None,
        );

        let on_click = Callback::new(|_id: String| {});
        let on_delete = Callback::new(|(_id, _name): (String, String)| {});

        view! {
            <Router>
                <CampaignCard
                    campaign=campaign
                    on_click=on_click
                    on_delete=on_delete
                />
            </Router>
        }
    });
}

// ============================================================================
// CampaignCardCompact Component Tests
// ============================================================================

#[wasm_bindgen_test]
fn test_campaign_card_compact_renders() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "compact-card",
            "Compact Campaign",
            "Blades in the Dark",
            None,
        );

        let on_click = Callback::new(|_id: String| {});

        view! {
            <Router>
                <CampaignCardCompact
                    campaign=campaign
                    on_click=on_click
                />
            </Router>
        }
    });
}

#[wasm_bindgen_test]
fn test_campaign_card_compact_active_state() {
    leptos::mount::mount_to_body(|| {
        provide_layout_state();

        let campaign = create_test_campaign(
            "active-compact",
            "Active Compact",
            "Vampire",
            None,
        );

        let on_click = Callback::new(|_id: String| {});

        view! {
            <Router>
                <CampaignCardCompact
                    campaign=campaign
                    is_active=true
                    on_click=on_click
                />
            </Router>
        }
    });
}

// ============================================================================
// Campaign Selection State Tests
// ============================================================================

#[wasm_bindgen_test]
fn test_campaign_selection_signal() {
    // Test that campaign selection can be tracked via reactive signals
    let selected_campaign = RwSignal::new(Option::<String>::None);

    // Initially no campaign is selected
    assert!(selected_campaign.get().is_none());

    // Select a campaign
    selected_campaign.set(Some("campaign-123".to_string()));
    assert_eq!(selected_campaign.get(), Some("campaign-123".to_string()));

    // Change selection
    selected_campaign.set(Some("campaign-456".to_string()));
    assert_eq!(selected_campaign.get(), Some("campaign-456".to_string()));

    // Deselect
    selected_campaign.set(None);
    assert!(selected_campaign.get().is_none());
}

#[wasm_bindgen_test]
fn test_multiple_campaign_selection() {
    // Test for multi-select scenarios (e.g., batch operations)
    let selected_campaigns = RwSignal::new(Vec::<String>::new());

    assert!(selected_campaigns.get().is_empty());

    // Add campaigns
    selected_campaigns.update(|v| v.push("campaign-1".to_string()));
    assert_eq!(selected_campaigns.get().len(), 1);

    selected_campaigns.update(|v| v.push("campaign-2".to_string()));
    assert_eq!(selected_campaigns.get().len(), 2);

    // Check contents
    let campaigns = selected_campaigns.get();
    assert!(campaigns.contains(&"campaign-1".to_string()));
    assert!(campaigns.contains(&"campaign-2".to_string()));

    // Remove one
    selected_campaigns.update(|v| v.retain(|c| c != "campaign-1"));
    assert_eq!(selected_campaigns.get().len(), 1);
    assert!(selected_campaigns.get().contains(&"campaign-2".to_string()));
}

#[wasm_bindgen_test]
fn test_active_campaign_state() {
    // Test tracking which campaign is currently "playing"
    let active_campaign_id = RwSignal::new(Option::<String>::None);

    // No active campaign initially
    assert!(active_campaign_id.get().is_none());

    // Start a session - campaign becomes active
    active_campaign_id.set(Some("playing-campaign".to_string()));
    assert_eq!(active_campaign_id.get(), Some("playing-campaign".to_string()));

    // End session - no active campaign
    active_campaign_id.set(None);
    assert!(active_campaign_id.get().is_none());
}
