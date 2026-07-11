/**
 * AUTO-GENERATED — DO NOT EDIT BY HAND.
 * Mirrors the backend FastAPI OpenAPI schema (backend/schemas.py).
 * Regenerate:   cd frontend && npm run gen:api-schema
 * Verify (CI):  cd frontend && npm run check:api-schema
 * Friendly aliases live in src/lib/api/types.ts (which derives from this file).
 */
export interface paths {
    "/admin/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/search/filter user accounts (admin) */
        get: operations["list_users_admin_users_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/admin/users/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** User-management audit trail (admin) */
        get: operations["user_audit_admin_users_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/admin/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Soft-delete an account — anonymize + retain for audit (admin) */
        delete: operations["delete_user_admin_users__user_id__delete"];
        options?: never;
        head?: never;
        /** Promote/demote role and/or enable/disable an account (admin) */
        patch: operations["update_user_admin_users__user_id__patch"];
        trace?: never;
    };
    "/admin/users/{user_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve a pending account (admin) */
        post: operations["approve_user_admin_users__user_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/admin/users/{user_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject a pending account (admin) */
        post: operations["reject_user_admin_users__user_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/activity/{entity_type}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Activity Summary */
        get: operations["activity_summary_ai_activity__entity_type___entity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ai Analytics */
        get: operations["ai_analytics_ai_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/briefings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Briefings */
        get: operations["list_briefings_ai_briefings_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/briefings/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Briefing */
        post: operations["generate_briefing_ai_briefings_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/briefings/latest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Latest Briefing */
        get: operations["latest_briefing_ai_briefings_latest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/copilot/customer/{account_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Customer Summary */
        get: operations["customer_summary_ai_copilot_customer__account_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/copilot/deal/{deal_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Deal Summary */
        get: operations["deal_summary_ai_copilot_deal__deal_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/copilot/executive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Executive Summary */
        get: operations["executive_summary_ai_copilot_executive_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/copilot/pipeline/{pipeline_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pipeline Summary */
        get: operations["pipeline_summary_ai_copilot_pipeline__pipeline_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/copilot/summary/{entity_type}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entity Summary */
        get: operations["entity_summary_ai_copilot_summary__entity_type___entity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ai Dashboard */
        get: operations["ai_dashboard_ai_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/engagement/compute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Compute Engagement */
        post: operations["compute_engagement_ai_engagement_compute_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/engagement/scores": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Engagement Scores */
        get: operations["list_engagement_scores_ai_engagement_scores_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/insights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Insights */
        get: operations["list_insights_ai_insights_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/insights/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Insights */
        post: operations["generate_insights_ai_insights_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/insights/{insight_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Insight */
        patch: operations["patch_insight_ai_insights__insight_id__patch"];
        trace?: never;
    };
    "/ai/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Recommendations */
        get: operations["list_recommendations_ai_recommendations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/recommendations/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Recommendations */
        post: operations["generate_recommendations_ai_recommendations_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/recommendations/{rec_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Recommendation */
        post: operations["complete_recommendation_ai_recommendations__rec_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/recommendations/{rec_id}/dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Recommendation */
        post: operations["dismiss_recommendation_ai_recommendations__rec_id__dismiss_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/risks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Risks */
        get: operations["list_risks_ai_risks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/risks/detect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Detect Risks */
        post: operations["detect_risks_ai_risks_detect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Cross-company smart alerts (Dashboard) */
        get: operations["list_alerts_alerts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/coverage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Engine-coverage matrix */
        get: operations["analytics_coverage_analytics_coverage_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Platform-wide rollup */
        get: operations["analytics_summary_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/assignments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** All assignments (manager+) */
        get: operations["list_all_assignments_get"];
        put?: never;
        /** Assign a lead to a user (manager+) */
        post: operations["create_assignments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/assignments/mine": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The current user's assigned leads */
        get: operations["list_mine_assignments_mine_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/assignments/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Assignable users (manager+) */
        get: operations["assignable_users_assignments_users_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/assignments/workload": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Per-user workload + unassigned high-grade count (manager+) */
        get: operations["workload_assignments_workload_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/assignments/{assignment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Unassign a lead (manager+) — logs an audit event */
        delete: operations["unassign_assignments__assignment_id__delete"];
        options?: never;
        head?: never;
        /** Update status/note (the assignee, or a manager+) */
        patch: operations["patch_assignments__assignment_id__patch"];
        trace?: never;
    };
    "/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign out (audit-only — app JWTs are stateless) */
        post: operations["logout_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current signed-in user */
        get: operations["me_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/microsoft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign in with Microsoft Entra ID */
        post: operations["microsoft_auth_microsoft_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh the session (issue a new app JWT) */
        post: operations["refresh_auth_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bi Analytics */
        get: operations["bi_analytics_bi_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bi Dashboard */
        get: operations["bi_dashboard_bi_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/dashboards/{dashboard_type}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Executive Dashboard */
        get: operations["executive_dashboard_bi_dashboards__dashboard_type__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/kpis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Kpis */
        get: operations["list_kpis_bi_kpis_get"];
        put?: never;
        /** Create Kpi */
        post: operations["create_kpi_bi_kpis_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/kpis/{kpi_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Kpi */
        delete: operations["delete_kpi_bi_kpis__kpi_id__delete"];
        options?: never;
        head?: never;
        /** Patch Kpi */
        patch: operations["patch_kpi_bi_kpis__kpi_id__patch"];
        trace?: never;
    };
    "/bi/kpis/{kpi_id}/values": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Kpi History */
        get: operations["kpi_history_bi_kpis__kpi_id__values_get"];
        put?: never;
        /** Record Kpi Value */
        post: operations["record_kpi_value_bi_kpis__kpi_id__values_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/reports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Reports */
        get: operations["list_reports_bi_reports_get"];
        put?: never;
        /** Create Report */
        post: operations["create_report_bi_reports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/reports/{report_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Report */
        delete: operations["delete_report_bi_reports__report_id__delete"];
        options?: never;
        head?: never;
        /** Patch Report */
        patch: operations["patch_report_bi_reports__report_id__patch"];
        trace?: never;
    };
    "/bi/reports/{report_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Run Report */
        get: operations["run_report_bi_reports__report_id__run_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/reports/{report_id}/schedules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Schedule */
        post: operations["create_schedule_bi_reports__report_id__schedules_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/schedules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Schedules */
        get: operations["list_schedules_bi_schedules_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/schedules/tick": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Due Schedules */
        post: operations["run_due_schedules_bi_schedules_tick_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/schedules/{schedule_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Schedule */
        delete: operations["delete_schedule_bi_schedules__schedule_id__delete"];
        options?: never;
        head?: never;
        /** Patch Schedule */
        patch: operations["patch_schedule_bi_schedules__schedule_id__patch"];
        trace?: never;
    };
    "/bi/schedules/{schedule_id}/deliver": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Deliver Schedule */
        post: operations["deliver_schedule_bi_schedules__schedule_id__deliver_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/schedules/{schedule_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["list_runs_bi_schedules__schedule_id__runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/trends/{metric}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Trend */
        get: operations["get_trend_bi_trends__metric__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/warehouse/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Warehouse */
        post: operations["refresh_warehouse_bi_warehouse_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bi/warehouse/snapshots": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Snapshots */
        get: operations["list_snapshots_bi_warehouse_snapshots_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Campaigns */
        get: operations["list_campaigns_campaigns_get"];
        put?: never;
        /** Create Campaign */
        post: operations["create_campaign_campaigns_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Dashboard */
        get: operations["get_dashboard_campaigns_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns/{campaign_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Campaign */
        get: operations["get_campaign_campaigns__campaign_id__get"];
        put?: never;
        post?: never;
        /** Delete Campaign */
        delete: operations["delete_campaign_campaigns__campaign_id__delete"];
        options?: never;
        head?: never;
        /** Patch Campaign */
        patch: operations["patch_campaign_campaigns__campaign_id__patch"];
        trace?: never;
    };
    "/campaigns/{campaign_id}/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Analytics */
        get: operations["get_analytics_campaigns__campaign_id__analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns/{campaign_id}/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Members */
        get: operations["list_members_campaigns__campaign_id__members_get"];
        put?: never;
        /** Add Member */
        post: operations["add_member_campaigns__campaign_id__members_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns/{campaign_id}/members/{member_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Member */
        delete: operations["remove_member_campaigns__campaign_id__members__member_id__delete"];
        options?: never;
        head?: never;
        /** Patch Member */
        patch: operations["patch_member_campaigns__campaign_id__members__member_id__patch"];
        trace?: never;
    };
    "/campaigns/{campaign_id}/members/{member_id}/enroll": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Enroll Member */
        post: operations["enroll_member_campaigns__campaign_id__members__member_id__enroll_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/campaigns/{campaign_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Timeline */
        get: operations["get_timeline_campaigns__campaign_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/companies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/search/filter companies */
        get: operations["list_companies_companies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/companies/{domain}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Unified company profile */
        get: operations["company_profile_companies__domain__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/companies/{domain}/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company activity timeline (notes + assignment events + score changes) */
        get: operations["activity_companies__domain__activity_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/companies/{domain}/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company notes */
        get: operations["list_notes_companies__domain__notes_get"];
        put?: never;
        /** Add a company note */
        post: operations["add_note_companies__domain__notes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Accounts */
        get: operations["list_accounts_cs_accounts_get"];
        put?: never;
        /** Create Account */
        post: operations["create_account_cs_accounts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Account */
        get: operations["get_account_cs_accounts__account_id__get"];
        put?: never;
        post?: never;
        /** Delete Account */
        delete: operations["delete_account_cs_accounts__account_id__delete"];
        options?: never;
        head?: never;
        /** Patch Account */
        patch: operations["patch_account_cs_accounts__account_id__patch"];
        trace?: never;
    };
    "/cs/accounts/{account_id}/contacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Contacts */
        get: operations["list_contacts_cs_accounts__account_id__contacts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Health */
        get: operations["get_health_cs_accounts__account_id__health_get"];
        put?: never;
        /** Score Account */
        post: operations["score_account_cs_accounts__account_id__health_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/health/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health History */
        get: operations["health_history_cs_accounts__account_id__health_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/lifecycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lifecycle History */
        get: operations["lifecycle_history_cs_accounts__account_id__lifecycle_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plans */
        get: operations["list_plans_cs_accounts__account_id__plans_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/risks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Risks */
        get: operations["list_risks_cs_accounts__account_id__risks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/accounts/{account_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Account Timeline */
        get: operations["account_timeline_cs_accounts__account_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Cs Analytics */
        get: operations["cs_analytics_cs_analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/contacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Contact */
        post: operations["create_contact_cs_contacts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/contacts/{contact_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Contact */
        delete: operations["delete_contact_cs_contacts__contact_id__delete"];
        options?: never;
        head?: never;
        /** Patch Contact */
        patch: operations["patch_contact_cs_contacts__contact_id__patch"];
        trace?: never;
    };
    "/cs/contracts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Contracts */
        get: operations["list_contracts_cs_contracts_get"];
        put?: never;
        /** Create Contract */
        post: operations["create_contract_cs_contracts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/contracts/{contract_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Contract */
        delete: operations["delete_contract_cs_contracts__contract_id__delete"];
        options?: never;
        head?: never;
        /** Patch Contract */
        patch: operations["patch_contract_cs_contracts__contract_id__patch"];
        trace?: never;
    };
    "/cs/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Cs Dashboard */
        get: operations["cs_dashboard_cs_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/milestones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Milestone */
        post: operations["create_milestone_cs_milestones_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/milestones/{milestone_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Milestone */
        delete: operations["delete_milestone_cs_milestones__milestone_id__delete"];
        options?: never;
        head?: never;
        /** Patch Milestone */
        patch: operations["patch_milestone_cs_milestones__milestone_id__patch"];
        trace?: never;
    };
    "/cs/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Plan */
        post: operations["create_plan_cs_plans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Plan */
        delete: operations["delete_plan_cs_plans__plan_id__delete"];
        options?: never;
        head?: never;
        /** Patch Plan */
        patch: operations["patch_plan_cs_plans__plan_id__patch"];
        trace?: never;
    };
    "/cs/plans/{plan_id}/milestones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Milestones */
        get: operations["list_milestones_cs_plans__plan_id__milestones_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/risks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Risk */
        post: operations["create_risk_cs_risks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/cs/risks/{risk_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Risk */
        delete: operations["delete_risk_cs_risks__risk_id__delete"];
        options?: never;
        head?: never;
        /** Patch Risk */
        patch: operations["patch_risk_cs_risks__risk_id__patch"];
        trace?: never;
    };
    "/custom-objects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Objects */
        get: operations["list_objects_custom_objects_get"];
        put?: never;
        /** Create Object */
        post: operations["create_object_custom_objects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Object Dashboard */
        get: operations["object_dashboard_custom_objects_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/fields/{field_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Field */
        delete: operations["delete_field_custom_objects_fields__field_id__delete"];
        options?: never;
        head?: never;
        /** Patch Field */
        patch: operations["patch_field_custom_objects_fields__field_id__patch"];
        trace?: never;
    };
    "/custom-objects/forms/{form_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Form */
        delete: operations["delete_form_custom_objects_forms__form_id__delete"];
        options?: never;
        head?: never;
        /** Patch Form */
        patch: operations["patch_form_custom_objects_forms__form_id__patch"];
        trace?: never;
    };
    "/custom-objects/{object_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Object */
        get: operations["get_object_custom_objects__object_id__get"];
        put?: never;
        post?: never;
        /** Delete Object */
        delete: operations["delete_object_custom_objects__object_id__delete"];
        options?: never;
        head?: never;
        /** Patch Object */
        patch: operations["patch_object_custom_objects__object_id__patch"];
        trace?: never;
    };
    "/custom-objects/{object_id}/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Object Analytics */
        get: operations["object_analytics_custom_objects__object_id__analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Records */
        get: operations["export_records_custom_objects__object_id__export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/fields": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Fields */
        get: operations["list_fields_custom_objects__object_id__fields_get"];
        put?: never;
        /** Create Field */
        post: operations["create_field_custom_objects__object_id__fields_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/forms": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Forms */
        get: operations["list_forms_custom_objects__object_id__forms_get"];
        put?: never;
        /** Create Form */
        post: operations["create_form_custom_objects__object_id__forms_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import records from a raw CSV body (Content-Type: text/csv) */
        post: operations["import_records_custom_objects__object_id__import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Data Jobs */
        get: operations["list_data_jobs_custom_objects__object_id__jobs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/records": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Records */
        get: operations["list_records_custom_objects__object_id__records_get"];
        put?: never;
        /** Create Record */
        post: operations["create_record_custom_objects__object_id__records_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/records/{record_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Record */
        get: operations["get_record_custom_objects__object_id__records__record_id__get"];
        put?: never;
        post?: never;
        /** Delete Record */
        delete: operations["delete_record_custom_objects__object_id__records__record_id__delete"];
        options?: never;
        head?: never;
        /** Patch Record */
        patch: operations["patch_record_custom_objects__object_id__records__record_id__patch"];
        trace?: never;
    };
    "/custom-objects/{object_id}/records/{record_id}/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Record Audit History */
        get: operations["record_audit_history_custom_objects__object_id__records__record_id__audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/custom-objects/{object_id}/records/{record_id}/related": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Related Records */
        get: operations["related_records_custom_objects__object_id__records__record_id__related_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/deals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Deals */
        get: operations["list_deals_deals_get"];
        put?: never;
        /** Create Deal */
        post: operations["create_deal_deals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/deals/{deal_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Deal */
        get: operations["get_deal_deals__deal_id__get"];
        put?: never;
        post?: never;
        /** Delete Deal */
        delete: operations["delete_deal_deals__deal_id__delete"];
        options?: never;
        head?: never;
        /** Patch Deal */
        patch: operations["patch_deal_deals__deal_id__patch"];
        trace?: never;
    };
    "/deals/{deal_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Deal History */
        get: operations["deal_history_deals__deal_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/deals/{deal_id}/intelligence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Deal Intelligence */
        get: operations["deal_intelligence_deals__deal_id__intelligence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/deals/{deal_id}/move": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move Deal */
        post: operations["move_deal_deals__deal_id__move_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/deals/{deal_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Deal Timeline */
        get: operations["deal_timeline_deals__deal_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/filter decision makers */
        get: operations["list_decision_makers_decision_makers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/companies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Decision-maker counts grouped by company */
        get: operations["decision_maker_companies_decision_makers_companies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/company/{domain}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ranked contacts + contact map + org hierarchy for a company (decision intelligence) */
        get: operations["company_contacts_decision_makers_company__domain__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/company/{domain}/intelligence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company intelligence bundle: committee/dept coverage, completeness, engagement, risk, heatmap, opportunity alignment, timeline */
        get: operations["company_intelligence_decision_makers_company__domain__intelligence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/company/{domain}/relationships": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Relationship intelligence: next best contacts/actions, follow-ups, opportunity intelligence, alerts and the relationship graph */
        get: operations["company_relationships_decision_makers_company__domain__relationships_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/{dm_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Full enrichment profile for one decision maker (lazy-loaded by the panel) */
        get: operations["get_decision_maker_decision_makers__dm_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/{dm_id}/contact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Professional contact details for a decision maker (any authenticated user) */
        get: operations["get_contact_decision_makers__dm_id__contact_get"];
        /** Set professional contact details (work email / phone only) — admin/manager only */
        put: operations["put_contact_decision_makers__dm_id__contact_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/{dm_id}/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Notes for a decision maker: all team notes + the caller's own personal notes */
        get: operations["list_notes_decision_makers__dm_id__notes_get"];
        put?: never;
        /** Add a note. 'team' notes require admin/manager; 'personal' notes are private to the author */
        post: operations["create_note_decision_makers__dm_id__notes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/decision-makers/{dm_id}/notes/{note_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete a note — team: admin/manager; personal: the author only */
        delete: operations["delete_note_decision_makers__dm_id__notes__note_id__delete"];
        options?: never;
        head?: never;
        /** Edit a note — team: admin/manager; personal: the author only */
        patch: operations["update_note_decision_makers__dm_id__notes__note_id__patch"];
        trace?: never;
    };
    "/demand-signals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/filter demand signals */
        get: operations["list_demand_signals_demand_signals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Enrollments */
        get: operations["list_enrollments_enrollments_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments/{enrollment_id}/advance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Advance */
        post: operations["advance_enrollments__enrollment_id__advance_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments/{enrollment_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel */
        post: operations["cancel_enrollments__enrollment_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments/{enrollment_id}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pause */
        post: operations["pause_enrollments__enrollment_id__pause_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments/{enrollment_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resume */
        post: operations["resume_enrollments__enrollment_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/enrollments/{enrollment_id}/steps/{step_id}/skip": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Skip Step */
        post: operations["skip_step_enrollments__enrollment_id__steps__step_id__skip_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Analytics */
        get: operations["admin_analytics_governance_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/api-keys": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Api Keys */
        get: operations["list_api_keys_governance_api_keys_get"];
        put?: never;
        /** Create Api Key */
        post: operations["create_api_key_governance_api_keys_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/api-keys/{key_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Api Key */
        post: operations["revoke_api_key_governance_api_keys__key_id__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/api-keys/{key_id}/rotate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rotate Api Key */
        post: operations["rotate_api_key_governance_api_keys__key_id__rotate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Audit Events */
        get: operations["list_audit_events_governance_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/compliance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Compliance Records */
        get: operations["list_compliance_records_governance_compliance_get"];
        put?: never;
        /** Create Compliance Record */
        post: operations["create_compliance_record_governance_compliance_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/compliance/soft-delete/{entity_type}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Soft Delete Entity */
        post: operations["soft_delete_entity_governance_compliance_soft_delete__entity_type___entity_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/compliance/{record_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Compliance Record */
        patch: operations["patch_compliance_record_governance_compliance__record_id__patch"];
        trace?: never;
    };
    "/governance/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Dashboard */
        get: operations["admin_dashboard_governance_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** System Health */
        get: operations["system_health_governance_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/organizations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Organizations */
        get: operations["list_organizations_governance_organizations_get"];
        put?: never;
        /** Create Organization */
        post: operations["create_organization_governance_organizations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/organizations/{org_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Organization */
        get: operations["get_organization_governance_organizations__org_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Organization */
        patch: operations["patch_organization_governance_organizations__org_id__patch"];
        trace?: never;
    };
    "/governance/organizations/{org_id}/units": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Units */
        get: operations["list_units_governance_organizations__org_id__units_get"];
        put?: never;
        /** Create Unit */
        post: operations["create_unit_governance_organizations__org_id__units_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/security/policies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Security Policies */
        get: operations["list_security_policies_governance_security_policies_get"];
        /** Upsert Security Policy */
        put: operations["upsert_security_policy_governance_security_policies_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Settings */
        get: operations["list_settings_governance_settings_get"];
        /** Upsert Setting */
        put: operations["upsert_setting_governance_settings_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/units/members/{member_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Member */
        delete: operations["remove_member_governance_units_members__member_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/governance/units/{unit_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Unit */
        delete: operations["delete_unit_governance_units__unit_id__delete"];
        options?: never;
        head?: never;
        /** Patch Unit */
        patch: operations["patch_unit_governance_units__unit_id__patch"];
        trace?: never;
    };
    "/governance/units/{unit_id}/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Members */
        get: operations["list_members_governance_units__unit_id__members_get"];
        put?: never;
        /** Add Member */
        post: operations["add_member_governance_units__unit_id__members_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Liveness + DB connectivity */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Liveness probe — process is up */
        get: operations["liveness_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Readiness probe — DB reachable */
        get: operations["readiness_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Integrations */
        get: operations["list_integrations_integrations_get"];
        put?: never;
        /** Create Integration */
        post: operations["create_integration_integrations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Integration Analytics */
        get: operations["integration_analytics_integrations_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/api-keys": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Api Keys */
        get: operations["list_api_keys_integrations_api_keys_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/connectors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Connectors */
        get: operations["list_connectors_integrations_connectors_get"];
        put?: never;
        /** Create Connector */
        post: operations["create_connector_integrations_connectors_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/connectors/{connector_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Connector */
        delete: operations["delete_connector_integrations_connectors__connector_id__delete"];
        options?: never;
        head?: never;
        /** Patch Connector */
        patch: operations["patch_connector_integrations_connectors__connector_id__patch"];
        trace?: never;
    };
    "/integrations/connectors/{connector_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Connector */
        post: operations["run_connector_integrations_connectors__connector_id__run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/connectors/{connector_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Connector Runs */
        get: operations["list_connector_runs_integrations_connectors__connector_id__runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Integration Dashboard */
        get: operations["integration_dashboard_integrations_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Events */
        get: operations["list_events_integrations_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/events/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish Event */
        post: operations["publish_event_integrations_events_publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/oauth-credentials": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Oauth Credentials */
        get: operations["list_oauth_credentials_integrations_oauth_credentials_get"];
        put?: never;
        /** Create Oauth Credential */
        post: operations["create_oauth_credential_integrations_oauth_credentials_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/oauth-credentials/{credential_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Oauth Credential */
        post: operations["revoke_oauth_credential_integrations_oauth_credentials__credential_id__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/oauth-credentials/{credential_id}/rotate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rotate Oauth Credential */
        post: operations["rotate_oauth_credential_integrations_oauth_credentials__credential_id__rotate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/plugins": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plugins */
        get: operations["list_plugins_integrations_plugins_get"];
        put?: never;
        /** Register Plugin */
        post: operations["register_plugin_integrations_plugins_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/plugins/executions/list": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plugin Executions */
        get: operations["list_plugin_executions_integrations_plugins_executions_list_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/plugins/hooks/{hook_name}/trigger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Trigger Plugin Hook */
        post: operations["trigger_plugin_hook_integrations_plugins_hooks__hook_name__trigger_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/plugins/{plugin_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Plugin */
        delete: operations["delete_plugin_integrations_plugins__plugin_id__delete"];
        options?: never;
        head?: never;
        /** Patch Plugin */
        patch: operations["patch_plugin_integrations_plugins__plugin_id__patch"];
        trace?: never;
    };
    "/integrations/webhooks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Webhooks */
        get: operations["list_webhooks_integrations_webhooks_get"];
        put?: never;
        /** Create Webhook */
        post: operations["create_webhook_integrations_webhooks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/webhooks/deliveries/list": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Deliveries */
        get: operations["list_deliveries_integrations_webhooks_deliveries_list_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/webhooks/deliveries/{delivery_id}/replay": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Replay Delivery */
        post: operations["replay_delivery_integrations_webhooks_deliveries__delivery_id__replay_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/webhooks/retry-tick": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Retry Tick */
        post: operations["run_retry_tick_integrations_webhooks_retry_tick_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/integrations/webhooks/{webhook_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Webhook */
        get: operations["get_webhook_integrations_webhooks__webhook_id__get"];
        put?: never;
        post?: never;
        /** Delete Webhook */
        delete: operations["delete_webhook_integrations_webhooks__webhook_id__delete"];
        options?: never;
        head?: never;
        /** Patch Webhook */
        patch: operations["patch_webhook_integrations_webhooks__webhook_id__patch"];
        trace?: never;
    };
    "/integrations/{integration_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Integration */
        get: operations["get_integration_integrations__integration_id__get"];
        put?: never;
        post?: never;
        /** Delete Integration */
        delete: operations["delete_integration_integrations__integration_id__delete"];
        options?: never;
        head?: never;
        /** Patch Integration */
        patch: operations["patch_integration_integrations__integration_id__patch"];
        trace?: never;
    };
    "/knowledge/articles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Articles */
        get: operations["list_articles_knowledge_articles_get"];
        put?: never;
        /** Create Article */
        post: operations["create_article_knowledge_articles_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Article */
        get: operations["get_article_knowledge_articles__article_id__get"];
        put?: never;
        post?: never;
        /** Delete Article */
        delete: operations["delete_article_knowledge_articles__article_id__delete"];
        options?: never;
        head?: never;
        /** Patch Article */
        patch: operations["patch_article_knowledge_articles__article_id__patch"];
        trace?: never;
    };
    "/knowledge/articles/{article_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Article */
        post: operations["archive_article_knowledge_articles__article_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Attachments */
        get: operations["list_attachments_knowledge_articles__article_id__attachments_get"];
        put?: never;
        /** Add Attachment */
        post: operations["add_attachment_knowledge_articles__article_id__attachments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish Article */
        post: operations["publish_article_knowledge_articles__article_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/related": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Related Articles */
        get: operations["related_articles_knowledge_articles__article_id__related_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit For Approval */
        post: operations["submit_for_approval_knowledge_articles__article_id__submit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Knowledge Summary */
        get: operations["knowledge_summary_knowledge_articles__article_id__summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/articles/{article_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Versions */
        get: operations["list_versions_knowledge_articles__article_id__versions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Categories */
        get: operations["list_categories_knowledge_categories_get"];
        put?: never;
        /** Create Category */
        post: operations["create_category_knowledge_categories_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/knowledge/categories/{category_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Category */
        delete: operations["delete_category_knowledge_categories__category_id__delete"];
        options?: never;
        head?: never;
        /** Patch Category */
        patch: operations["patch_category_knowledge_categories__category_id__patch"];
        trace?: never;
    };
    "/knowledge/context-suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Context Suggestions */
        get: operations["context_suggestions_knowledge_context_suggestions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/leadership-signals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/filter person-level leadership-movement signals (director+) */
        get: operations["list_leadership_signals_leadership_signals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/leads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Leads ranked by lead score */
        get: operations["list_leads_leads_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/dataset/build": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Build the training dataset from the trailing 30–90 days (no training) */
        post: operations["build_dataset_ml_dataset_build_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/features/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Incrementally (re)build the feature store */
        post: operations["refresh_features_ml_features_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/features/{company_domain}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Feature vector for a company (cached or computed on demand) */
        get: operations["feature_vector_ml_features__company_domain__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/inference/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run offline inference (probabilities stored alongside the lead score) */
        post: operations["run_inference_ml_inference_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/interactions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List feedback interactions */
        get: operations["list_interactions_ml_interactions_get"];
        put?: never;
        /** Record a user feedback interaction (thumbs up/down/export/contact/ignore) */
        post: operations["record_interaction_ml_interactions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Model registry */
        get: operations["list_models_ml_models_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/models/{version}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Model detail (metrics + feature importance + hyperparameters) */
        get: operations["get_model_ml_models__version__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/models/{version}/promote": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Promote a candidate to production (gated: thresholds + outperform) */
        post: operations["promote_ml_models__version__promote_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/models/{version}/rollback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Roll back production to a previous model version */
        post: operations["rollback_ml_models__version__rollback_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Offline inference recommendations (separate from the lead score) */
        get: operations["list_recommendations_ml_recommendations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** ML foundation status + counts */
        get: operations["ml_status_ml_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ml/train": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Train a candidate model from the dataset builder (no auto-promotion) */
        post: operations["train_ml_train_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List/filter opportunities */
        get: operations["list_opportunities_opportunities_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities/news-sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Configured news sources */
        get: operations["list_news_sources_opportunities_news_sources_get"];
        put?: never;
        /** Add a news source (RSS / Google Alerts URL) — DB-driven config */
        post: operations["create_news_source_opportunities_news_sources_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities/news-sources/seed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Idempotently seed the curated production news feeds */
        post: operations["seed_news_sources_opportunities_news_sources_seed_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities/news-sources/{source_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update / enable / disable a news source */
        patch: operations["update_news_source_opportunities_news_sources__source_id__patch"];
        trace?: never;
    };
    "/opportunities/{opportunity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Full opportunity intelligence (summaries, entities, sources, related, timeline, reviews) */
        get: operations["get_opportunity_opportunities__opportunity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities/{opportunity_id}/lifecycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Set opportunity lifecycle (New/Active/Monitoring/Resolved/Archived) */
        post: operations["set_lifecycle_opportunities__opportunity_id__lifecycle_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/opportunities/{opportunity_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply a manual-review action (not_relevant/merge/split/change_type/archive/restore/note) */
        post: operations["review_opportunity_opportunities__opportunity_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pipeline funnel + mail metrics */
        get: operations["analytics_outreach_analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/analytics/company/{company_domain}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get per-company outreach analytics */
        get: operations["company_analytics_outreach_analytics_company__company_domain__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/analytics/template/{template_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get per-template outreach analytics */
        get: operations["template_analytics_outreach_analytics_template__template_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/analytics/user/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get per-user outreach analytics */
        get: operations["user_analytics_outreach_analytics_user__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/approvals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Messages pending approval */
        get: operations["approvals_outreach_approvals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/intelligence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get all outreach intelligence for a company */
        get: operations["get_campaign_intelligence_outreach_companies__company_domain__intelligence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/contacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get ranked contact recommendations for outreach */
        get: operations["recommend_contacts_outreach_companies__company_domain__recommendations_contacts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/priority": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get outreach priority classification */
        get: operations["get_priority_outreach_companies__company_domain__recommendations_priority_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/send-time": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get recommended send time for outreach */
        get: operations["recommend_send_time_outreach_companies__company_domain__recommendations_send_time_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/sequence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get recommended outreach sequence */
        get: operations["get_sequence_outreach_companies__company_domain__recommendations_sequence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/subjects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get recommended email subjects */
        get: operations["recommend_subjects_outreach_companies__company_domain__recommendations_subjects_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/success-probability": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Estimate conversion probability */
        get: operations["estimate_success_outreach_companies__company_domain__recommendations_success_probability_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/companies/{company_domain}/recommendations/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get recommended email templates */
        get: operations["recommend_templates_outreach_companies__company_domain__recommendations_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/contacts/{dm_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Full contact history for a decision maker */
        get: operations["contact_history_outreach_contacts__dm_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List conversations (folder, search, label aware) */
        get: operations["list_conversations_outreach_conversations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/bulk": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk action on conversations (archive|restore|trash|apply_label|remove_label) */
        post: operations["bulk_conversation_action_outreach_conversations_bulk_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get conversation detail */
        get: operations["get_conversation_outreach_conversations__conv_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive a conversation */
        post: operations["archive_conversation_outreach_conversations__conv_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/labels/{label_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply a label to a conversation */
        post: operations["apply_label_outreach_conversations__conv_id__labels__label_id__post"];
        /** Remove a label from a conversation */
        delete: operations["remove_label_outreach_conversations__conv_id__labels__label_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** All messages in a conversation (chronological) */
        get: operations["conversation_messages_outreach_conversations__conv_id__messages_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore an archived/trashed conversation */
        post: operations["restore_conversation_outreach_conversations__conv_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Unified email + meeting + task + note timeline for a conversation's lead */
        get: operations["conversation_timeline_outreach_conversations__conv_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/conversations/{conv_id}/trash": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move a conversation to trash */
        post: operations["trash_conversation_outreach_conversations__conv_id__trash_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Outreach dashboard widgets */
        get: operations["dashboard_outreach_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/follow-ups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Upcoming + overdue follow-ups */
        get: operations["follow_ups_outreach_follow_ups_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/auth-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Generate Gmail OAuth authorization URL (starts the connect flow) */
        get: operations["gmail_auth_url_outreach_gmail_auth_url_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Gmail OAuth callback — exchange authorization code for tokens */
        get: operations["gmail_callback_outreach_gmail_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/disconnect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Disconnect Gmail — revoke stored tokens */
        post: operations["gmail_disconnect_outreach_gmail_disconnect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/refresh-token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Manually refresh the Gmail access token */
        post: operations["gmail_refresh_token_outreach_gmail_refresh_token_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Gmail connection status for the current user */
        get: operations["gmail_status_outreach_gmail_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/gmail/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Trigger a manual Gmail sync for the current user */
        post: operations["gmail_sync_outreach_gmail_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/inbox": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Outreach threads + replies */
        get: operations["inbox_outreach_inbox_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/labels": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List all labels (system + custom) */
        get: operations["list_labels_outreach_labels_get"];
        put?: never;
        /** Create a custom label (admin/manager) */
        post: operations["create_label_outreach_labels_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/labels/{label_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete a custom label (admin/manager; system labels cannot be deleted) */
        delete: operations["delete_label_outreach_labels__label_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List outreach pipeline leads */
        get: operations["list_leads_outreach_leads_get"];
        put?: never;
        /** Qualify a company into the outreach pipeline (idempotent) */
        post: operations["create_lead_outreach_leads_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sync top Discovery leads into the pipeline (admin/manager) */
        post: operations["sync_from_discovery_outreach_leads_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads/{lead_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Outreach lead detail */
        get: operations["get_lead_outreach_leads__lead_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update stage / owner / service / next action */
        patch: operations["patch_lead_outreach_leads__lead_id__patch"];
        trace?: never;
    };
    "/outreach/leads/{lead_id}/activities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Activity timeline for a lead */
        get: operations["lead_activities_outreach_leads__lead_id__activities_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads/{lead_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Messages (drafts + sent + replies) for a lead */
        get: operations["lead_messages_outreach_leads__lead_id__messages_get"];
        put?: never;
        /** Create a draft (optionally from a template) */
        post: operations["create_message_outreach_leads__lead_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads/{lead_id}/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add a note to a lead's activity timeline */
        post: operations["add_note_outreach_leads__lead_id__notes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/leads/{lead_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Unified activity + meeting + task timeline for a lead */
        get: operations["lead_timeline_outreach_leads__lead_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/meetings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List meetings */
        get: operations["list_meetings_outreach_meetings_get"];
        put?: never;
        /** Log a meeting or call */
        post: operations["create_meeting_outreach_meetings_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/meetings/{meeting_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Meeting detail */
        get: operations["get_meeting_outreach_meetings__meeting_id__get"];
        put?: never;
        post?: never;
        /** Delete a meeting */
        delete: operations["delete_meeting_outreach_meetings__meeting_id__delete"];
        options?: never;
        head?: never;
        /** Update a meeting */
        patch: operations["patch_meeting_outreach_meetings__meeting_id__patch"];
        trace?: never;
    };
    "/outreach/messages/bulk": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk action on messages (archive|restore|trash|mark_read|mark_unread) */
        post: operations["bulk_message_action_outreach_messages_bulk_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete a draft (author or manager) */
        delete: operations["delete_draft_outreach_messages__message_id__delete"];
        options?: never;
        head?: never;
        /** Edit a draft */
        patch: operations["patch_message_outreach_messages__message_id__patch"];
        trace?: never;
    };
    "/outreach/messages/{message_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve a pending message (admin/manager) */
        post: operations["approve_message_outreach_messages__message_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive a message */
        post: operations["archive_message_outreach_messages__message_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List attachments for a message */
        get: operations["list_attachments_outreach_messages__message_id__attachments_get"];
        put?: never;
        /** Upload an attachment (base64) */
        post: operations["add_attachment_outreach_messages__message_id__attachments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/attachments/{attachment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get attachment metadata + content (base64) */
        get: operations["get_attachment_outreach_messages__message_id__attachments__attachment_id__get"];
        put?: never;
        post?: never;
        /** Remove an attachment */
        delete: operations["remove_attachment_outreach_messages__message_id__attachments__attachment_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel a scheduled or queued message (admin/manager) */
        post: operations["cancel_message_outreach_messages__message_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/duplicate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Duplicate a message as a new draft */
        post: operations["duplicate_draft_outreach_messages__message_id__duplicate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/forward": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create a forward draft from an existing message */
        post: operations["forward_message_outreach_messages__message_id__forward_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/pin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pin a message */
        post: operations["pin_message_outreach_messages__message_id__pin_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sanitized message preview (safe HTML + plain text + attachment list) */
        get: operations["message_preview_outreach_messages__message_id__preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark message as read */
        post: operations["mark_read_outreach_messages__message_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/reply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Simulate an inbound reply (mock-mail demo) */
        post: operations["simulate_reply_outreach_messages__message_id__reply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/reply-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create a reply draft from an existing message */
        post: operations["reply_to_message_outreach_messages__message_id__reply_draft_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore an archived/trashed message */
        post: operations["restore_message_outreach_messages__message_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/schedule": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Schedule an approved message for future sending (admin/manager) */
        post: operations["schedule_message_outreach_messages__message_id__schedule_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/send": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Send an approved message via the configured mailer (admin/manager) */
        post: operations["send_message_outreach_messages__message_id__send_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/star": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Star a message */
        post: operations["star_message_outreach_messages__message_id__star_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit a draft for approval */
        post: operations["submit_message_outreach_messages__message_id__submit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/trash": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move message to trash */
        post: operations["trash_message_outreach_messages__message_id__trash_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/unpin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Unpin a message */
        post: operations["unpin_message_outreach_messages__message_id__unpin_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/unread": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark message as unread */
        post: operations["mark_unread_outreach_messages__message_id__unread_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/messages/{message_id}/unstar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Remove star from a message */
        post: operations["unstar_message_outreach_messages__message_id__unstar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/provider": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get current user's email provider config */
        get: operations["get_provider_outreach_provider_get"];
        /** Set email provider config (admin/manager) */
        put: operations["set_provider_outreach_provider_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/scheduler/tick": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run one scheduler cycle — advance scheduled→queued, cancel overdue (admin/manager) */
        post: operations["scheduler_tick_outreach_scheduler_tick_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search messages (subject, body, sender, recipient, folder, status, date) */
        get: operations["search_messages_outreach_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List tasks */
        get: operations["list_tasks_outreach_tasks_get"];
        put?: never;
        /** Create a task */
        post: operations["create_task_outreach_tasks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get task detail */
        get: operations["get_task_outreach_tasks__task_id__get"];
        put?: never;
        post?: never;
        /** Delete a task */
        delete: operations["delete_task_outreach_tasks__task_id__delete"];
        options?: never;
        head?: never;
        /** Update a task */
        patch: operations["patch_task_outreach_tasks__task_id__patch"];
        trace?: never;
    };
    "/outreach/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List email templates */
        get: operations["list_templates_outreach_templates_get"];
        put?: never;
        /** Create a template (admin/manager) */
        post: operations["create_template_outreach_templates_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/outreach/templates/{template_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update a template (admin/manager) */
        put: operations["update_template_outreach_templates__template_id__put"];
        post?: never;
        /** Delete a template (admin/manager) */
        delete: operations["delete_template_outreach_templates__template_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipeline/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Per-component freshness */
        get: operations["health_pipeline_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipeline/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recent pipeline runs */
        get: operations["runs_pipeline_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipeline/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Data freshness + latest run status */
        get: operations["status_pipeline_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Pipelines */
        get: operations["list_pipelines_pipelines_get"];
        put?: never;
        /** Create Pipeline */
        post: operations["create_pipeline_pipelines_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Dashboard */
        get: operations["get_dashboard_pipelines_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/{pipeline_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Pipeline */
        get: operations["get_pipeline_pipelines__pipeline_id__get"];
        put?: never;
        post?: never;
        /** Delete Pipeline */
        delete: operations["delete_pipeline_pipelines__pipeline_id__delete"];
        options?: never;
        head?: never;
        /** Patch Pipeline */
        patch: operations["patch_pipeline_pipelines__pipeline_id__patch"];
        trace?: never;
    };
    "/pipelines/{pipeline_id}/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Analytics */
        get: operations["get_analytics_pipelines__pipeline_id__analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/{pipeline_id}/forecast": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Forecast */
        get: operations["get_forecast_pipelines__pipeline_id__forecast_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/{pipeline_id}/kanban": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Kanban */
        get: operations["kanban_pipelines__pipeline_id__kanban_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/{pipeline_id}/stages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Stage */
        post: operations["add_stage_pipelines__pipeline_id__stages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/pipelines/{pipeline_id}/stages/{stage_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Stage */
        delete: operations["delete_stage_pipelines__pipeline_id__stages__stage_id__delete"];
        options?: never;
        head?: never;
        /** Patch Stage */
        patch: operations["patch_stage_pipelines__pipeline_id__stages__stage_id__patch"];
        trace?: never;
    };
    "/platform/config/readiness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Production configuration readiness (Phase 13) */
        get: operations["production_readiness_platform_config_readiness_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/platform/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Production dashboard: status/sessions/auth/queues/integrations */
        get: operations["production_dashboard_platform_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/platform/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Operational health: app/db/scheduler/integrations/auth/cache */
        get: operations["operational_health_platform_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/platform/validate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Final platform validation — one reachability check per module */
        get: operations["platform_validate_platform_validate_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List review-queue items */
        get: operations["list_items_review_queue_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One review item */
        get: operations["get_item_review_queue__review_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}/actions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit trail */
        get: operations["get_actions_review_queue__review_id__actions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}/alias": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create a name->domain alias */
        post: operations["create_alias_review_queue__review_id__alias_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm the stub company */
        post: operations["approve_review_queue__review_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}/merge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Merge stub into a canonical company */
        post: operations["merge_review_queue__review_id__merge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-queue/{review_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject (not a prospect) */
        post: operations["reject_review_queue__review_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reviews/reports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Model-vs-human review reports (disagreements, overrides, strategic, false neg/pos) */
        get: operations["reports_reviews_reports_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reviews/{domain}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The current human assessment of a lead (null if unreviewed) */
        get: operations["get_review_reviews__domain__get"];
        /** Set/update the human assessment (does NOT change the model score) */
        put: operations["put_review_reviews__domain__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reviews/{domain}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The review audit trail for a company (who, when, status change, notes) */
        get: operations["history_reviews__domain__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/bi/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Bi Summary */
        get: operations["get_bi_summary_revops_bi_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/executive-dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Executive Dashboard */
        get: operations["get_executive_dashboard_revops_executive_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/forecast": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Revenue Forecast */
        get: operations["get_revenue_forecast_revops_forecast_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/forecast/accuracy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Forecast Accuracy */
        get: operations["get_forecast_accuracy_revops_forecast_accuracy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/forecast/snapshots": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Forecast Snapshot */
        post: operations["post_forecast_snapshot_revops_forecast_snapshots_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/funnels": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Funnel Analytics */
        get: operations["get_funnel_analytics_revops_funnels_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/pipeline-analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Pipeline Analytics */
        get: operations["get_pipeline_analytics_revops_pipeline_analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/reports/{report_type}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Executive Report */
        get: operations["get_executive_report_revops_reports__report_type__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/sales-performance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sales Performance */
        get: operations["get_sales_performance_revops_sales_performance_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/targets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Revenue Targets */
        get: operations["list_revenue_targets_revops_targets_get"];
        put?: never;
        /** Create Revenue Target */
        post: operations["create_revenue_target_revops_targets_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/targets/{target_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Revenue Target */
        get: operations["get_revenue_target_revops_targets__target_id__get"];
        put?: never;
        post?: never;
        /** Delete Revenue Target */
        delete: operations["delete_revenue_target_revops_targets__target_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revops/targets/{target_id}/attainment": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Target Attainment */
        get: operations["get_target_attainment_revops_targets__target_id__attainment_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scheduler/run-now": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Trigger a Standard Run now (manager+) */
        post: operations["run_now_scheduler_run_now_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scheduler/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Run history (most recent first) */
        get: operations["list_runs_scheduler_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scheduler/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One run's full detail */
        get: operations["get_run_scheduler_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scheduler/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Scheduler status + next run + last run */
        get: operations["get_status_scheduler_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Global Search */
        get: operations["global_search_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Analytics */
        get: operations["search_analytics_search_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Dashboard */
        get: operations["search_dashboard_search_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/full-text": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Full Text Search */
        get: operations["full_text_search_search_full_text_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/recent": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recent Searches */
        get: operations["recent_searches_search_recent_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/saved": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Saved Searches */
        get: operations["list_saved_searches_search_saved_get"];
        put?: never;
        /** Create Saved Search */
        post: operations["create_saved_search_search_saved_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/saved/{search_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Saved Search */
        delete: operations["delete_saved_search_search_saved__search_id__delete"];
        options?: never;
        head?: never;
        /** Patch Saved Search */
        patch: operations["patch_saved_search_search_saved__search_id__patch"];
        trace?: never;
    };
    "/search/saved/{search_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Saved Search */
        post: operations["run_saved_search_search_saved__search_id__run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/similar-records": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Similar Records */
        get: operations["similar_records_search_similar_records_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sequences": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sequences */
        get: operations["list_sequences_sequences_get"];
        put?: never;
        /** Create Sequence */
        post: operations["create_sequence_sequences_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sequences/{seq_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sequence */
        get: operations["get_sequence_sequences__seq_id__get"];
        put?: never;
        post?: never;
        /** Delete Sequence */
        delete: operations["delete_sequence_sequences__seq_id__delete"];
        options?: never;
        head?: never;
        /** Patch Sequence */
        patch: operations["patch_sequence_sequences__seq_id__patch"];
        trace?: never;
    };
    "/sequences/{seq_id}/steps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Step */
        post: operations["add_step_sequences__seq_id__steps_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sequences/{seq_id}/steps/{step_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Step */
        delete: operations["delete_step_sequences__seq_id__steps__step_id__delete"];
        options?: never;
        head?: never;
        /** Patch Step */
        patch: operations["patch_step_sequences__seq_id__steps__step_id__patch"];
        trace?: never;
    };
    "/team/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Workload Analytics */
        get: operations["workload_analytics_team_analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/assignments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Assignment */
        post: operations["create_assignment_team_assignments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/assignments/{assignment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Assignment */
        delete: operations["delete_assignment_team_assignments__assignment_id__delete"];
        options?: never;
        head?: never;
        /** Patch Assignment */
        patch: operations["patch_assignment_team_assignments__assignment_id__patch"];
        trace?: never;
    };
    "/team/assignments/{entity_type}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Entity Assignments */
        get: operations["list_entity_assignments_team_assignments__entity_type___entity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/assignments/{entity_type}/{entity_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Assignment History */
        get: operations["assignment_history_team_assignments__entity_type___entity_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/comments/{comment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Comment */
        delete: operations["delete_comment_team_comments__comment_id__delete"];
        options?: never;
        head?: never;
        /** Patch Comment */
        patch: operations["patch_comment_team_comments__comment_id__patch"];
        trace?: never;
    };
    "/team/comments/{entity_type}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Comments */
        get: operations["list_comments_team_comments__entity_type___entity_id__get"];
        put?: never;
        /** Create Comment */
        post: operations["create_comment_team_comments__entity_type___entity_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Team Dashboard */
        get: operations["team_dashboard_team_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/feed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Activity Feed */
        get: operations["activity_feed_team_feed_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notifications */
        get: operations["list_notifications_team_notifications_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/notifications/read-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark All Read */
        post: operations["mark_all_read_team_notifications_read_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/notifications/{notif_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Read */
        post: operations["mark_read_team_notifications__notif_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/saved-views": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Saved Views */
        get: operations["list_saved_views_team_saved_views_get"];
        put?: never;
        /** Create Saved View */
        post: operations["create_saved_view_team_saved_views_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/team/saved-views/{view_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Saved View */
        delete: operations["delete_saved_view_team_saved_views__view_id__delete"];
        options?: never;
        head?: never;
        /** Patch Saved View */
        patch: operations["patch_saved_view_team_saved_views__view_id__patch"];
        trace?: never;
    };
    "/team/work-queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Work Queue */
        get: operations["work_queue_team_work_queue_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Workflows */
        get: operations["list_workflows_workflows_get"];
        put?: never;
        /** Create Workflow */
        post: operations["create_workflow_workflows_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/analytics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Workflow Analytics */
        get: operations["workflow_analytics_workflows_analytics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/approvals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Approval */
        post: operations["create_approval_workflows_approvals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/approvals/list": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Approvals */
        get: operations["list_approvals_workflows_approvals_list_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/approvals/{approval_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Approval */
        get: operations["get_approval_workflows_approvals__approval_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/approvals/{approval_id}/decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide Approval */
        post: operations["decide_approval_workflows_approvals__approval_id__decide_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Workflow Dashboard */
        get: operations["workflow_dashboard_workflows_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/executions/list": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Executions */
        get: operations["list_executions_workflows_executions_list_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/scan/renewals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Fire contract_renewal_window workflows for contracts nearing expiry (manual or cron-tick) */
        post: operations["scan_renewals_workflows_scan_renewals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/sla/policies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sla Policies */
        get: operations["list_sla_policies_workflows_sla_policies_get"];
        put?: never;
        /** Create Sla Policy */
        post: operations["create_sla_policy_workflows_sla_policies_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/sla/policies/{policy_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Sla Policy */
        patch: operations["patch_sla_policy_workflows_sla_policies__policy_id__patch"];
        trace?: never;
    };
    "/workflows/sla/tick": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run one SLA sweep — mark at_risk/breached/escalated (manual or cron-tick) */
        post: operations["sla_tick_workflows_sla_tick_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/sla/trackers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sla Trackers */
        get: operations["list_sla_trackers_workflows_sla_trackers_get"];
        put?: never;
        /** Create Sla Tracker */
        post: operations["create_sla_tracker_workflows_sla_trackers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/sla/trackers/{tracker_id}/resolve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Sla Tracker */
        post: operations["resolve_sla_tracker_workflows_sla_trackers__tracker_id__resolve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workflows/{workflow_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Workflow */
        get: operations["get_workflow_workflows__workflow_id__get"];
        put?: never;
        post?: never;
        /** Delete Workflow */
        delete: operations["delete_workflow_workflows__workflow_id__delete"];
        options?: never;
        head?: never;
        /** Patch Workflow */
        patch: operations["patch_workflow_workflows__workflow_id__patch"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** ActivityItem */
        ActivityItem: {
            /**
             * Actor
             * @default
             */
            actor: string;
            /** At */
            at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Kind */
            kind: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** AdminAnalyticsOut */
        AdminAnalyticsOut: {
            /**
             * Api Utilization
             * @default {}
             */
            api_utilization: {
                [key: string]: number;
            };
            /**
             * Audit Volume By Category
             * @default {}
             */
            audit_volume_by_category: {
                [key: string]: number;
            };
            /**
             * Compliance Stats
             * @default {}
             */
            compliance_stats: {
                [key: string]: number;
            };
            /**
             * Login Activity By Period
             * @default {}
             */
            login_activity_by_period: {
                [key: string]: number;
            };
            /**
             * Security Events By Type
             * @default {}
             */
            security_events_by_type: {
                [key: string]: number;
            };
            /**
             * User Growth By Period
             * @default {}
             */
            user_growth_by_period: {
                [key: string]: number;
            };
            /**
             * Workflow Utilization
             * @default {}
             */
            workflow_utilization: {
                [key: string]: number;
            };
        };
        /** AdminDashboardOut */
        AdminDashboardOut: {
            /**
             * Active Users
             * @default 0
             */
            active_users: number;
            /**
             * Api Usage Total
             * @default 0
             */
            api_usage_total: number;
            /**
             * Audit Events 24H
             * @default 0
             */
            audit_events_24h: number;
            /**
             * Pending Compliance Requests
             * @default 0
             */
            pending_compliance_requests: number;
            /**
             * Security Events 24H
             * @default 0
             */
            security_events_24h: number;
            system_health: components["schemas"]["SystemHealthOut"];
            /**
             * Total Organizations
             * @default 0
             */
            total_organizations: number;
        };
        /** AiAnalyticsOut */
        AiAnalyticsOut: {
            /** Avg Engagement Score */
            avg_engagement_score?: number | null;
            /**
             * Copilot Usage By Type
             * @default {}
             */
            copilot_usage_by_type: {
                [key: string]: number;
            };
            /**
             * Engagement Trend Counts
             * @default {}
             */
            engagement_trend_counts: {
                [key: string]: number;
            };
            /**
             * Executive Briefings Generated
             * @default 0
             */
            executive_briefings_generated: number;
            /**
             * Insight Counts
             * @default {}
             */
            insight_counts: {
                [key: string]: number;
            };
            /**
             * Recommendation Acceptance
             * @default []
             */
            recommendation_acceptance: components["schemas"]["AiRecommendationAcceptanceOut"][];
            /**
             * Risk Distribution
             * @default {}
             */
            risk_distribution: {
                [key: string]: number;
            };
        };
        /** AiBriefingOut */
        AiBriefingOut: {
            /** Generated At */
            generated_at?: string | null;
            /** Generated By */
            generated_by?: number | null;
            /** Id */
            id: number;
            /**
             * Period
             * @default
             */
            period: string;
            /**
             * Sections
             * @default {}
             */
            sections: {
                [key: string]: unknown;
            };
        };
        /** AiCopilotSummaryOut */
        AiCopilotSummaryOut: {
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Query Type */
            query_type: string;
            /** Summary */
            summary: string;
        };
        /** AiDashboardOut */
        AiDashboardOut: {
            /**
             * Active Insights
             * @default 0
             */
            active_insights: number;
            /**
             * Active Risks
             * @default 0
             */
            active_risks: number;
            /** Avg Engagement Score */
            avg_engagement_score?: number | null;
            latest_briefing?: components["schemas"]["AiBriefingOut"] | null;
            /**
             * Pending Recommendations
             * @default 0
             */
            pending_recommendations: number;
            /**
             * Recent Ai Activity
             * @default []
             */
            recent_ai_activity: components["schemas"]["AiInsightOut"][];
        };
        /** AiGenerationResultOut */
        AiGenerationResultOut: {
            /**
             * Generated
             * @default 0
             */
            generated: number;
        };
        /** AiInsightOut */
        AiInsightOut: {
            /** Confidence */
            confidence: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Generated At */
            generated_at?: string | null;
            /** Id */
            id: number;
            /** Insight Type */
            insight_type: string;
            /** Severity */
            severity: string;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** AiInsightPatch */
        AiInsightPatch: {
            /** Status */
            status: string;
        };
        /** AiRecommendationAcceptanceOut */
        AiRecommendationAcceptanceOut: {
            /**
             * Acceptance Rate
             * @default 0
             */
            acceptance_rate: number;
            /**
             * Completed
             * @default 0
             */
            completed: number;
            /**
             * Dismissed
             * @default 0
             */
            dismissed: number;
            /** Recommendation Type */
            recommendation_type: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** AiRecommendationOut */
        AiRecommendationOut: {
            /** Completed At */
            completed_at?: string | null;
            /** Completed By */
            completed_by?: number | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Dismissed At */
            dismissed_at?: string | null;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Generated At */
            generated_at?: string | null;
            /** Id */
            id: number;
            /**
             * Priority
             * @default medium
             */
            priority: string;
            /** Recommendation Type */
            recommendation_type: string;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** AlertOut */
        AlertOut: {
            /**
             * At
             * @default
             */
            at: string;
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Severity
             * @default info
             */
            severity: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Type */
            type: string;
        };
        /** AliasBody */
        AliasBody: {
            /** Company Domain */
            company_domain: string;
            /** Name */
            name: string;
        };
        /** AnalyticsCoverage */
        AnalyticsCoverage: {
            /** Signal Distribution */
            signal_distribution: {
                [key: string]: number;
            };
            /** Total Companies */
            total_companies: number;
            /** With All Three */
            with_all_three: number;
            /** With Decision Makers */
            with_decision_makers: number;
            /** With Demand */
            with_demand: number;
            /** With Lead Score */
            with_lead_score: number;
            /** With Opportunities */
            with_opportunities: number;
        };
        /** AnalyticsSummary */
        AnalyticsSummary: {
            /** Grade Distribution */
            grade_distribution: {
                [key: string]: number;
            };
            /** Top Companies */
            top_companies: components["schemas"]["LeadOut"][];
            /** Total Companies */
            total_companies: number;
            /** Total Decision Makers */
            total_decision_makers: number;
            /** Total Demand Signals */
            total_demand_signals: number;
            /** Total Jobs */
            total_jobs: number;
            /** Total Leads */
            total_leads: number;
            /** Total Opportunities */
            total_opportunities: number;
        };
        /** ApiKeyCreate */
        ApiKeyCreate: {
            /** Expires At */
            expires_at?: string | null;
            /** Name */
            name: string;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
        };
        /** ApiKeyCreatedOut */
        ApiKeyCreatedOut: {
            /** Api Key */
            api_key: string;
            /** Created At */
            created_at?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Id */
            id: number;
            /** Key Prefix */
            key_prefix: string;
            /** Name */
            name: string;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
            /** Status */
            status: string;
        };
        /** ApiKeyOut */
        ApiKeyOut: {
            /** Created At */
            created_at?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Id */
            id: number;
            /** Key Prefix */
            key_prefix: string;
            /** Last Used At */
            last_used_at?: string | null;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Request Count
             * @default 0
             */
            request_count: number;
            /** Revoked At */
            revoked_at?: string | null;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
            /** Status */
            status: string;
        };
        /** ApprovalDecisionIn */
        ApprovalDecisionIn: {
            /**
             * Comments
             * @default
             */
            comments: string;
            /** Decision */
            decision: string;
        };
        /** ApprovalRequestCreate */
        ApprovalRequestCreate: {
            /** Approval Type */
            approval_type: string;
            /** Approver Id */
            approver_id?: number | null;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
        };
        /** ApprovalRequestOut */
        ApprovalRequestOut: {
            /** Approval Type */
            approval_type: string;
            /**
             * Approver Email
             * @default
             */
            approver_email: string;
            /** Approver Id */
            approver_id?: number | null;
            /** Decided At */
            decided_at?: string | null;
            /**
             * Decision Reason
             * @default
             */
            decision_reason: string;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Id */
            id: number;
            /** Requested At */
            requested_at?: string | null;
            /** Requested By */
            requested_by?: number | null;
            /**
             * Requested By Email
             * @default
             */
            requested_by_email: string;
            /** Status */
            status: string;
            /** Workflow Execution Id */
            workflow_execution_id?: number | null;
        };
        /** AssignmentCreate */
        AssignmentCreate: {
            /** Company Domain */
            company_domain: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Status
             * @default assigned
             */
            status: string;
            /** User Id */
            user_id: number;
        };
        /** AssignmentOut */
        AssignmentOut: {
            /** Assigned By */
            assigned_by?: number | null;
            /**
             * Assigned By Email
             * @default
             */
            assigned_by_email: string;
            /**
             * Assigned By Name
             * @default
             */
            assigned_by_name: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Created At */
            created_at?: string | null;
            /** Grade */
            grade?: string | null;
            /** Id */
            id: number;
            /** Lead Score */
            lead_score?: number | null;
            /**
             * Note
             * @default
             */
            note: string;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * User Email
             * @default
             */
            user_email: string;
            /** User Id */
            user_id: number;
            /**
             * User Name
             * @default
             */
            user_name: string;
        };
        /** AssignmentPatch */
        AssignmentPatch: {
            /** Note */
            note?: string | null;
            /** Status */
            status?: string | null;
        };
        /** AuthResult */
        AuthResult: {
            /** Token */
            token: string;
            user: components["schemas"]["UserOut"];
        };
        /** BiAnalyticsOut */
        BiAnalyticsOut: {
            /**
             * Dashboard Usage
             * @default {}
             */
            dashboard_usage: {
                [key: string]: number;
            };
            /**
             * Forecast Trends
             * @default {}
             */
            forecast_trends: {
                [key: string]: number;
            };
            /**
             * Growth Rates
             * @default {}
             */
            growth_rates: {
                [key: string]: number;
            };
            /**
             * Kpi Achievement
             * @default {}
             */
            kpi_achievement: {
                [key: string]: number;
            };
            /**
             * Report Usage
             * @default {}
             */
            report_usage: {
                [key: string]: number;
            };
            /**
             * Warehouse Statistics
             * @default {}
             */
            warehouse_statistics: {
                [key: string]: number;
            };
        };
        /** BiDashboardOut */
        BiDashboardOut: {
            /** Data Freshness */
            data_freshness?: string | null;
            /**
             * Executive Metrics
             * @default {}
             */
            executive_metrics: {
                [key: string]: {
                    [key: string]: unknown;
                };
            };
            /**
             * Kpis
             * @default []
             */
            kpis: components["schemas"]["KpiOut"][];
            /**
             * Scheduled Reports Count
             * @default 0
             */
            scheduled_reports_count: number;
            /**
             * Trends
             * @default []
             */
            trends: components["schemas"]["TrendOut"][];
            /**
             * Warehouse Snapshots Count
             * @default 0
             */
            warehouse_snapshots_count: number;
        };
        /** BiExecutiveDashboardOut */
        BiExecutiveDashboardOut: {
            /** Dashboard Type */
            dashboard_type: string;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /**
             * Metrics
             * @default {}
             */
            metrics: {
                [key: string]: unknown;
            };
        };
        /** BiSummaryOut */
        BiSummaryOut: {
            executive_dashboard: components["schemas"]["ExecutiveDashboardOut"];
            funnels: components["schemas"]["FunnelAnalyticsOut"];
            /**
             * Revenue Trend
             * @default []
             */
            revenue_trend: {
                [key: string]: unknown;
            }[];
            sales_performance: components["schemas"]["SalesPerformanceOut"];
        };
        /** BulkConversationIn */
        BulkConversationIn: {
            /** Action */
            action: string;
            /** Conversation Ids */
            conversation_ids: number[];
            /** Label Id */
            label_id?: number | null;
        };
        /** BulkMessageIn */
        BulkMessageIn: {
            /** Action */
            action: string;
            /** Message Ids */
            message_ids: number[];
        };
        /** BulkOperationOut */
        BulkOperationOut: {
            /** Action */
            action: string;
            /** Affected */
            affected: number;
        };
        /** BuyingCommitteeOut */
        BuyingCommitteeOut: {
            /**
             * Coverage Pct
             * @default 0
             */
            coverage_pct: number;
            /**
             * Present
             * @default 0
             */
            present: number;
            /**
             * Roles
             * @default []
             */
            roles: components["schemas"]["CommitteeRoleOut"][];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** CampaignAnalyticsOut */
        CampaignAnalyticsOut: {
            /**
             * Active Members
             * @default 0
             */
            active_members: number;
            /** Campaign Id */
            campaign_id: number;
            /**
             * Campaign Name
             * @default
             */
            campaign_name: string;
            /**
             * Companies Contacted
             * @default 0
             */
            companies_contacted: number;
            /**
             * Conversion Rate
             * @default 0
             */
            conversion_rate: number;
            /**
             * Converted
             * @default 0
             */
            converted: number;
            /**
             * Decision Makers Contacted
             * @default 0
             */
            decision_makers_contacted: number;
            /**
             * Emails Sent
             * @default 0
             */
            emails_sent: number;
            /**
             * Meeting Rate
             * @default 0
             */
            meeting_rate: number;
            /**
             * Meetings
             * @default 0
             */
            meetings: number;
            /**
             * Replies
             * @default 0
             */
            replies: number;
            /**
             * Reply Rate
             * @default 0
             */
            reply_rate: number;
            /**
             * Sequence Completion Rate
             * @default 0
             */
            sequence_completion_rate: number;
            /**
             * Total Members
             * @default 0
             */
            total_members: number;
        };
        /** CampaignCreate */
        CampaignCreate: {
            /** Budget */
            budget?: number | null;
            /**
             * Campaign Type
             * @default cold_outreach
             */
            campaign_type: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** End Date */
            end_date?: string | null;
            /**
             * Goal
             * @default
             */
            goal: string;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Start Date */
            start_date?: string | null;
            /**
             * Tags
             * @default []
             */
            tags: string[];
        };
        /** CampaignDashboardOut */
        CampaignDashboardOut: {
            /**
             * Active Campaigns
             * @default 0
             */
            active_campaigns: number;
            /**
             * Campaigns
             * @default []
             */
            campaigns: components["schemas"]["CampaignOut"][];
            /**
             * Emails Sent
             * @default 0
             */
            emails_sent: number;
            /**
             * Meetings
             * @default 0
             */
            meetings: number;
            /**
             * Overall Reply Rate
             * @default 0
             */
            overall_reply_rate: number;
            /**
             * Replies
             * @default 0
             */
            replies: number;
            /**
             * Total Members
             * @default 0
             */
            total_members: number;
        };
        /** CampaignIntelligenceOut */
        CampaignIntelligenceOut: {
            best_contact?: components["schemas"]["ContactRecommendationOut"] | null;
            best_send_time?: components["schemas"]["SendTimeRecommendationOut"] | null;
            /**
             * Best Subjects
             * @default []
             */
            best_subjects: components["schemas"]["SubjectRecommendationOut"][];
            best_template?: components["schemas"]["TemplateRecommendationOut"] | null;
            outreach_priority?: components["schemas"]["OutreachPriorityOut"] | null;
            success_probability?: components["schemas"]["SuccessProbabilityOut"] | null;
        };
        /** CampaignMemberIn */
        CampaignMemberIn: {
            /** Company Domain */
            company_domain?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /** Opportunity Id */
            opportunity_id?: string | null;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
        };
        /** CampaignMemberOut */
        CampaignMemberOut: {
            /** Campaign Id */
            campaign_id: number;
            /**
             * Campaign Outcome
             * @default
             */
            campaign_outcome: string;
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Current Stage
             * @default pending
             */
            current_stage: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Decision Maker Name
             * @default
             */
            decision_maker_name: string;
            /**
             * Engagement Status
             * @default active
             */
            engagement_status: string;
            /** Id */
            id: number;
            /** Joined At */
            joined_at?: string | null;
            /** Last Activity At */
            last_activity_at?: string | null;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Opportunity Id */
            opportunity_id?: string | null;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CampaignMemberPatch */
        CampaignMemberPatch: {
            /** Campaign Outcome */
            campaign_outcome?: string | null;
            /** Current Stage */
            current_stage?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /** Engagement Status */
            engagement_status?: string | null;
            /** Notes */
            notes?: string | null;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
        };
        /** CampaignOut */
        CampaignOut: {
            /**
             * Active Count
             * @default 0
             */
            active_count: number;
            /** Budget */
            budget?: number | null;
            /**
             * Campaign Type
             * @default cold_outreach
             */
            campaign_type: string;
            /**
             * Converted Count
             * @default 0
             */
            converted_count: number;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Created By Email
             * @default
             */
            created_by_email: string;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Emails Sent
             * @default 0
             */
            emails_sent: number;
            /** End Date */
            end_date?: string | null;
            /**
             * Goal
             * @default
             */
            goal: string;
            /** Id */
            id: number;
            /**
             * Meetings
             * @default 0
             */
            meetings: number;
            /**
             * Member Count
             * @default 0
             */
            member_count: number;
            /** Name */
            name: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Replies
             * @default 0
             */
            replies: number;
            /** Start Date */
            start_date?: string | null;
            /**
             * Status
             * @default draft
             */
            status: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Updated At */
            updated_at?: string | null;
        };
        /** CampaignPatch */
        CampaignPatch: {
            /** Budget */
            budget?: number | null;
            /** Campaign Type */
            campaign_type?: string | null;
            /** Description */
            description?: string | null;
            /** End Date */
            end_date?: string | null;
            /** Goal */
            goal?: string | null;
            /** Name */
            name?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Start Date */
            start_date?: string | null;
            /** Status */
            status?: string | null;
            /** Tags */
            tags?: string[] | null;
        };
        /** CommentCreate */
        CommentCreate: {
            /** Body */
            body: string;
            /**
             * Mentions
             * @default []
             */
            mentions: number[];
            /** Parent Id */
            parent_id?: number | null;
        };
        /** CommentOut */
        CommentOut: {
            /**
             * Author Email
             * @default
             */
            author_email: string;
            /** Author Id */
            author_id?: number | null;
            /** Body */
            body: string;
            /** Created At */
            created_at?: string | null;
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /** Id */
            id: number;
            /**
             * Is Edited
             * @default false
             */
            is_edited: boolean;
            /**
             * Mentions
             * @default []
             */
            mentions: number[];
            /** Parent Id */
            parent_id?: number | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CommentPatch */
        CommentPatch: {
            /** Body */
            body?: string | null;
        };
        /** CommitteeRoleOut */
        CommitteeRoleOut: {
            contact?: components["schemas"]["ContactRefOut"] | null;
            /**
             * Present
             * @default false
             */
            present: boolean;
            /** Role */
            role: string;
        };
        /**
         * CompanyContactsOut
         * @description Decision-intelligence view of a company's contacts: ranked recommendations,
         *     the auto-grouped contact map, and the inferred org hierarchy.
         */
        CompanyContactsOut: {
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Groups
             * @default []
             */
            groups: components["schemas"]["ContactGroupOut"][];
            /**
             * Hierarchy
             * @default []
             */
            hierarchy: components["schemas"]["HierarchyLevelOut"][];
            /**
             * Recommended
             * @default []
             */
            recommended: components["schemas"]["RankedContactOut"][];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /**
         * CompanyIntelligenceOut
         * @description The Company Intelligence panel bundle (Phase 2.5).
         */
        CompanyIntelligenceOut: {
            buying_committee: components["schemas"]["BuyingCommitteeOut"];
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            contact_completeness: components["schemas"]["ContactCompletenessOut"];
            contact_risk: components["schemas"]["ContactRiskOut"];
            department_coverage: components["schemas"]["DepartmentCoverageOut"];
            engagement: components["schemas"]["EngagementScoreOut"];
            /**
             * Opportunity Alignment
             * @default []
             */
            opportunity_alignment: components["schemas"]["OppAlignmentOut"][];
            /**
             * Relationship Heatmap
             * @default []
             */
            relationship_heatmap: components["schemas"]["HeatmapRowOut"][];
            /**
             * Timeline
             * @default []
             */
            timeline: components["schemas"]["TimelineEventOut"][];
            /**
             * Total Contacts
             * @default 0
             */
            total_contacts: number;
        };
        /** CompanyNoteIn */
        CompanyNoteIn: {
            /** Body */
            body: string;
        };
        /** CompanyNoteOut */
        CompanyNoteOut: {
            /**
             * Author Email
             * @default
             */
            author_email: string;
            /** Author User Id */
            author_user_id?: number | null;
            /**
             * Body
             * @default
             */
            body: string;
            /** Company Domain */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
        };
        /** CompanyOut */
        CompanyOut: {
            /** Canonical Company Id */
            canonical_company_id: string;
            /**
             * City
             * @default
             */
            city: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Linkedin
             * @default
             */
            company_linkedin: string;
            /** Company Name */
            company_name: string;
            /**
             * Company Status
             * @default
             */
            company_status: string;
            /** Company Tier */
            company_tier: string;
            /** Compliance Flag */
            compliance_flag: string;
            /**
             * Confidence Score
             * @default 0
             */
            confidence_score: number;
            /**
             * Country
             * @default
             */
            country: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Founded Year
             * @default
             */
            founded_year: string;
            /**
             * Headquarters
             * @default
             */
            headquarters: string;
            /**
             * Industry Category
             * @default
             */
            industry_category: string;
            /** Is Stub */
            is_stub: boolean;
            /** Prospect Type */
            prospect_type: string;
            /**
             * Source
             * @default
             */
            source: string;
            /**
             * Sub Category
             * @default
             */
            sub_category: string;
            /**
             * Technology Focus
             * @default
             */
            technology_focus: string;
            /** Updated At */
            updated_at?: string | null;
            /** Validation Status */
            validation_status: string;
            /**
             * Website
             * @default
             */
            website: string;
        };
        /**
         * CompanyProfile
         * @description The unified view — every engine's data for one company, joined on domain.
         */
        CompanyProfile: {
            company: components["schemas"]["CompanyOut"];
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /**
             * Decision Makers
             * @default []
             */
            decision_makers: components["schemas"]["DecisionMakerOut"][];
            demand_signal?: components["schemas"]["DemandSignalOut"] | null;
            engagement?: components["schemas"]["EngagementOut"] | null;
            /**
             * Jobs
             * @default []
             */
            jobs: components["schemas"]["JobOut"][];
            lead_review?: components["schemas"]["LeadReviewOut"] | null;
            /**
             * Lead Review History
             * @default []
             */
            lead_review_history: components["schemas"]["LeadReviewEventOut"][];
            lead_score?: components["schemas"]["LeadScoreOut"] | null;
            /**
             * Leadership Signals
             * @default []
             */
            leadership_signals: components["schemas"]["LeadershipSignalOut"][];
            /**
             * Opportunities
             * @default []
             */
            opportunities: components["schemas"]["OpportunityOut"][];
            /**
             * Review Feedback Enabled
             * @default false
             */
            review_feedback_enabled: boolean;
            review_status: components["schemas"]["ReviewStatusOut"];
        };
        /** CompanyRelationshipsOut */
        CompanyRelationshipsOut: {
            /**
             * Alerts
             * @default []
             */
            alerts: components["schemas"]["AlertOut"][];
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Follow Ups
             * @default []
             */
            follow_ups: components["schemas"]["NextBestContactOut"][];
            graph: components["schemas"]["RelationshipGraphOut"];
            /**
             * Next Best Contacts
             * @default []
             */
            next_best_contacts: components["schemas"]["NextBestContactOut"][];
            /**
             * Opportunity Intelligence
             * @default []
             */
            opportunity_intelligence: components["schemas"]["OppIntelOut"][];
        };
        /** CompanySummary */
        CompanySummary: {
            /** Company Domain */
            company_domain: string;
            /** Company Name */
            company_name: string;
            /** Company Tier */
            company_tier: string;
            /** Compliance Flag */
            compliance_flag: string;
            /**
             * Country
             * @default
             */
            country: string;
            /** Grade */
            grade?: string | null;
            /** Is Stub */
            is_stub: boolean;
            /** Lead Score */
            lead_score?: number | null;
            /** Prospect Type */
            prospect_type: string;
            /** Validation Status */
            validation_status: string;
        };
        /** ComplianceRecordCreate */
        ComplianceRecordCreate: {
            /**
             * Detail
             * @default {}
             */
            detail: {
                [key: string]: unknown;
            };
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Record Type */
            record_type: string;
        };
        /** ComplianceRecordOut */
        ComplianceRecordOut: {
            /**
             * Detail
             * @default {}
             */
            detail: {
                [key: string]: unknown;
            };
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Id */
            id: number;
            /** Record Type */
            record_type: string;
            /** Requested At */
            requested_at?: string | null;
            /** Requested By */
            requested_by?: number | null;
            /** Resolved At */
            resolved_at?: string | null;
            /** Status */
            status: string;
        };
        /** ComplianceRecordPatch */
        ComplianceRecordPatch: {
            /** Status */
            status: string;
        };
        /** ConnectorCreate */
        ConnectorCreate: {
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /** Connector Type */
            connector_type: string;
            /** Name */
            name: string;
            /**
             * Schedule Cron
             * @default
             */
            schedule_cron: string;
        };
        /** ConnectorHealthOut */
        ConnectorHealthOut: {
            /** Connector Id */
            connector_id: number;
            /** Connector Type */
            connector_type: string;
            /** Last Run At */
            last_run_at?: string | null;
            /**
             * Last Run Status
             * @default
             */
            last_run_status: string;
            /** Name */
            name: string;
            /** Status */
            status: string;
        };
        /** ConnectorOut */
        ConnectorOut: {
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /** Connector Type */
            connector_type: string;
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /** Last Run At */
            last_run_at?: string | null;
            /**
             * Last Run Status
             * @default
             */
            last_run_status: string;
            /** Name */
            name: string;
            /**
             * Schedule Cron
             * @default
             */
            schedule_cron: string;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** ConnectorPatch */
        ConnectorPatch: {
            /** Config */
            config?: {
                [key: string]: unknown;
            } | null;
            /** Name */
            name?: string | null;
            /** Schedule Cron */
            schedule_cron?: string | null;
            /** Status */
            status?: string | null;
        };
        /** ConnectorRunOut */
        ConnectorRunOut: {
            /** Completed At */
            completed_at?: string | null;
            /** Connector Id */
            connector_id: number;
            /**
             * Duration Ms
             * @default 0
             */
            duration_ms: number;
            /** Id */
            id: number;
            /**
             * Result Detail
             * @default {}
             */
            result_detail: {
                [key: string]: unknown;
            };
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
        };
        /** ContactCompletenessOut */
        ContactCompletenessOut: {
            /**
             * Avg Confidence
             * @default 0
             */
            avg_confidence: number;
            /**
             * Avg Influence
             * @default 0
             */
            avg_influence: number;
            /**
             * High Confidence Pct
             * @default 0
             */
            high_confidence_pct: number;
            /**
             * Linkedin Pct
             * @default 0
             */
            linkedin_pct: number;
            /**
             * Missing Email
             * @default 0
             */
            missing_email: number;
            /**
             * Missing Linkedin
             * @default 0
             */
            missing_linkedin: number;
            /**
             * Missing Phone
             * @default 0
             */
            missing_phone: number;
            /**
             * Phone Pct
             * @default 0
             */
            phone_pct: number;
            /**
             * Total Contacts
             * @default 0
             */
            total_contacts: number;
            /**
             * Verified Email Pct
             * @default 0
             */
            verified_email_pct: number;
        };
        /**
         * ContactGroupOut
         * @description A Company Contact Map bucket (Executive, Engineering Leaders, …).
         */
        ContactGroupOut: {
            /**
             * Contacts
             * @default []
             */
            contacts: components["schemas"]["RankedContactOut"][];
            /** Group */
            group: string;
        };
        /** ContactHistoryOut */
        ContactHistoryOut: {
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Emails Received
             * @default 0
             */
            emails_received: number;
            /**
             * Emails Sent
             * @default 0
             */
            emails_sent: number;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /** Last Contacted At */
            last_contacted_at?: string | null;
            /**
             * Meetings Count
             * @default 0
             */
            meetings_count: number;
            /**
             * Notes Count
             * @default 0
             */
            notes_count: number;
            /**
             * Tasks Count
             * @default 0
             */
            tasks_count: number;
            /**
             * Timeline
             * @default []
             */
            timeline: components["schemas"]["UnifiedTimelineEvent"][];
            /**
             * Title
             * @default
             */
            title: string;
        };
        /**
         * ContactIn
         * @description Professional contact details only — work email / phone. No personal data.
         */
        ContactIn: {
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Work Email
             * @default
             */
            work_email: string;
            /**
             * Work Phone
             * @default
             */
            work_phone: string;
        };
        /** ContactOut */
        ContactOut: {
            /** Added By */
            added_by?: number | null;
            /**
             * Added By Email
             * @default
             */
            added_by_email: string;
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Email Overridden
             * @default false
             */
            email_overridden: boolean;
            /**
             * From Source
             * @default false
             */
            from_source: boolean;
            /** Id */
            id: number;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Phone Overridden
             * @default false
             */
            phone_overridden: boolean;
            /**
             * Source Work Email
             * @default
             */
            source_work_email: string;
            /**
             * Source Work Phone
             * @default
             */
            source_work_phone: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Work Email
             * @default
             */
            work_email: string;
            /**
             * Work Phone
             * @default
             */
            work_phone: string;
        };
        /** ContactRecommendationOut */
        ContactRecommendationOut: {
            /**
             * Company Engagement
             * @default
             */
            company_engagement: string;
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /**
             * Confidence Score
             * @default 0
             */
            confidence_score: number;
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Email
             * @default
             */
            email: string;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /**
             * Influence Score
             * @default 0
             */
            influence_score: number;
            /**
             * Recommendation Reason
             * @default []
             */
            recommendation_reason: string[];
            /**
             * Relationship Strength
             * @default 0
             */
            relationship_strength: number;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /**
         * ContactRefOut
         * @description A compact decision-maker reference carrying its computed intelligence.
         */
        ContactRefOut: {
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /** Confidence Score */
            confidence_score?: number | null;
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Department
             * @default
             */
            department: string;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /** Influence Score */
            influence_score?: number | null;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** ContactRiskItemOut */
        ContactRiskItemOut: {
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Risks
             * @default []
             */
            risks: string[];
        };
        /** ContactRiskOut */
        ContactRiskOut: {
            /**
             * Duplicates
             * @default 0
             */
            duplicates: number;
            /**
             * Items
             * @default []
             */
            items: components["schemas"]["ContactRiskItemOut"][];
            /**
             * Leadership Departures
             * @default 0
             */
            leadership_departures: number;
            /**
             * Low Confidence
             * @default 0
             */
            low_confidence: number;
            /**
             * Missing Email
             * @default 0
             */
            missing_email: number;
            /**
             * Missing Linkedin
             * @default 0
             */
            missing_linkedin: number;
            /**
             * Missing Phone
             * @default 0
             */
            missing_phone: number;
            /**
             * Stale
             * @default 0
             */
            stale: number;
        };
        /** ContextSuggestionOut */
        ContextSuggestionOut: {
            /**
             * Articles
             * @default []
             */
            articles: components["schemas"]["RelatedArticleOut"][];
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
        };
        /** CrmAssignmentCreate */
        CrmAssignmentCreate: {
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Role
             * @default assignee
             */
            role: string;
            /** User Id */
            user_id: number;
        };
        /** CrmAssignmentHistoryOut */
        CrmAssignmentHistoryOut: {
            /** Action */
            action: string;
            /** Changed By */
            changed_by?: number | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /** Id */
            id: number;
            /**
             * Role
             * @default
             */
            role: string;
            /**
             * User Email
             * @default
             */
            user_email: string;
            /** User Id */
            user_id?: number | null;
        };
        /** CrmAssignmentOut */
        CrmAssignmentOut: {
            /** Assigned By */
            assigned_by?: number | null;
            /** Created At */
            created_at?: string | null;
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /** Id */
            id: number;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Role
             * @default assignee
             */
            role: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * User Email
             * @default
             */
            user_email: string;
            /** User Id */
            user_id: number;
        };
        /** CrmAssignmentPatch */
        CrmAssignmentPatch: {
            /** Note */
            note?: string | null;
            /** Role */
            role?: string | null;
        };
        /** CrmEnrollmentOut */
        CrmEnrollmentOut: {
            /** Campaign Id */
            campaign_id?: number | null;
            /** Campaign Member Id */
            campaign_member_id?: number | null;
            /**
             * Campaign Name
             * @default
             */
            campaign_name: string;
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Completed At */
            completed_at?: string | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Current Step
             * @default 0
             */
            current_step: number;
            /** Id */
            id: number;
            /** Next Step At */
            next_step_at?: string | null;
            /** Outreach Lead Id */
            outreach_lead_id: number;
            /** Sequence Id */
            sequence_id: number;
            /**
             * Sequence Name
             * @default
             */
            sequence_name: string;
            /**
             * Status
             * @default active
             */
            status: string;
            /**
             * Step Count
             * @default 0
             */
            step_count: number;
        };
        /** CrmSequenceCreate */
        CrmSequenceCreate: {
            /**
             * Description
             * @default
             */
            description: string;
            /** Name */
            name: string;
        };
        /** CrmSequenceOut */
        CrmSequenceOut: {
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /** Name */
            name: string;
            /**
             * Step Count
             * @default 0
             */
            step_count: number;
            /**
             * Steps
             * @default []
             */
            steps: components["schemas"]["CrmSequenceStepOut"][];
            /** Updated At */
            updated_at?: string | null;
        };
        /** CrmSequencePatch */
        CrmSequencePatch: {
            /** Description */
            description?: string | null;
            /** Is Active */
            is_active?: boolean | null;
            /** Name */
            name?: string | null;
        };
        /** CrmSequenceStepIn */
        CrmSequenceStepIn: {
            /** Action */
            action: string;
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /**
             * Delay Days
             * @default 0
             */
            delay_days: number;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Name
             * @default
             */
            name: string;
            /** Step Order */
            step_order: number;
            /** Template Id */
            template_id?: number | null;
        };
        /** CrmSequenceStepOut */
        CrmSequenceStepOut: {
            /** Action */
            action: string;
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /** Created At */
            created_at?: string | null;
            /**
             * Delay Days
             * @default 0
             */
            delay_days: number;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /**
             * Name
             * @default
             */
            name: string;
            /** Sequence Id */
            sequence_id: number;
            /** Step Order */
            step_order: number;
            /** Template Id */
            template_id?: number | null;
        };
        /** CrmSequenceStepPatch */
        CrmSequenceStepPatch: {
            /** Action */
            action?: string | null;
            /** Config */
            config?: {
                [key: string]: unknown;
            } | null;
            /** Delay Days */
            delay_days?: number | null;
            /** Description */
            description?: string | null;
            /** Name */
            name?: string | null;
            /** Step Order */
            step_order?: number | null;
            /** Template Id */
            template_id?: number | null;
        };
        /** CsAccountCreate */
        CsAccountCreate: {
            /**
             * Arr
             * @default 0
             */
            arr: number;
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Contract Value
             * @default 0
             */
            contract_value: number;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /**
             * Industry
             * @default
             */
            industry: string;
            /**
             * Lifecycle Stage
             * @default customer
             */
            lifecycle_stage: string;
            /**
             * Mrr
             * @default 0
             */
            mrr: number;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Renewal Date */
            renewal_date?: string | null;
            /**
             * Status
             * @default active
             */
            status: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /**
             * Tier
             * @default mid_market
             */
            tier: string;
        };
        /** CsAccountOut */
        CsAccountOut: {
            /**
             * Arr
             * @default 0
             */
            arr: number;
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Contract Value
             * @default 0
             */
            contract_value: number;
            /** Created At */
            created_at?: string | null;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** Health Grade */
            health_grade?: string | null;
            /** Health Score */
            health_score?: number | null;
            /** Health Trend */
            health_trend?: string | null;
            /** Id */
            id: number;
            /**
             * Industry
             * @default
             */
            industry: string;
            /**
             * Lifecycle Stage
             * @default customer
             */
            lifecycle_stage: string;
            /**
             * Mrr
             * @default 0
             */
            mrr: number;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Renewal Date */
            renewal_date?: string | null;
            /**
             * Status
             * @default active
             */
            status: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /**
             * Tier
             * @default mid_market
             */
            tier: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CsAccountPatch */
        CsAccountPatch: {
            /** Arr */
            arr?: number | null;
            /** Company Domain */
            company_domain?: string | null;
            /** Contract Value */
            contract_value?: number | null;
            /** Currency */
            currency?: string | null;
            /** Industry */
            industry?: string | null;
            /** Lifecycle Stage */
            lifecycle_stage?: string | null;
            /** Mrr */
            mrr?: number | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Renewal Date */
            renewal_date?: string | null;
            /** Status */
            status?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Tier */
            tier?: string | null;
        };
        /** CsAnalyticsOut */
        CsAnalyticsOut: {
            /**
             * Active Count
             * @default 0
             */
            active_count: number;
            /** Avg Health Score */
            avg_health_score?: number | null;
            /**
             * By Status
             * @default {}
             */
            by_status: {
                [key: string]: number;
            };
            /**
             * Churn Count
             * @default 0
             */
            churn_count: number;
            /**
             * Churn Rate
             * @default 0
             */
            churn_rate: number;
            /**
             * Expansion Account Count
             * @default 0
             */
            expansion_account_count: number;
            /**
             * Health Distribution
             * @default {}
             */
            health_distribution: {
                [key: string]: number;
            };
            /**
             * Renewal Rate
             * @default 0
             */
            renewal_rate: number;
            /**
             * Total Arr
             * @default 0
             */
            total_arr: number;
            /**
             * Total Mrr
             * @default 0
             */
            total_mrr: number;
        };
        /** CsContactCreate */
        CsContactCreate: {
            /** Account Id */
            account_id: number;
            /**
             * Email
             * @default
             */
            email: string;
            /**
             * First Name
             * @default
             */
            first_name: string;
            /**
             * Is Primary
             * @default false
             */
            is_primary: boolean;
            /**
             * Last Name
             * @default
             */
            last_name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Phone
             * @default
             */
            phone: string;
            /**
             * Role
             * @default primary
             */
            role: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** CsContactOut */
        CsContactOut: {
            /** Account Id */
            account_id: number;
            /** Created At */
            created_at?: string | null;
            /**
             * Email
             * @default
             */
            email: string;
            /**
             * First Name
             * @default
             */
            first_name: string;
            /** Id */
            id: number;
            /**
             * Is Primary
             * @default false
             */
            is_primary: boolean;
            /**
             * Last Name
             * @default
             */
            last_name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Phone
             * @default
             */
            phone: string;
            /**
             * Role
             * @default primary
             */
            role: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CsContactPatch */
        CsContactPatch: {
            /** Email */
            email?: string | null;
            /** First Name */
            first_name?: string | null;
            /** Is Primary */
            is_primary?: boolean | null;
            /** Last Name */
            last_name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Phone */
            phone?: string | null;
            /** Role */
            role?: string | null;
            /** Title */
            title?: string | null;
        };
        /** CsContractCreate */
        CsContractCreate: {
            /** Account Id */
            account_id: number;
            /**
             * Auto Renew
             * @default false
             */
            auto_renew: boolean;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** End Date */
            end_date?: string | null;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Renewal Probability
             * @default 0.5
             */
            renewal_probability: number;
            /** Start Date */
            start_date?: string | null;
            /**
             * Status
             * @default active
             */
            status: string;
            /**
             * Value
             * @default 0
             */
            value: number;
        };
        /** CsContractOut */
        CsContractOut: {
            /** Account Id */
            account_id: number;
            /**
             * Auto Renew
             * @default false
             */
            auto_renew: boolean;
            /** Created At */
            created_at?: string | null;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** End Date */
            end_date?: string | null;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Renewal Probability
             * @default 0.5
             */
            renewal_probability: number;
            /** Start Date */
            start_date?: string | null;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Value
             * @default 0
             */
            value: number;
        };
        /** CsContractPatch */
        CsContractPatch: {
            /** Auto Renew */
            auto_renew?: boolean | null;
            /** Currency */
            currency?: string | null;
            /** End Date */
            end_date?: string | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Renewal Probability */
            renewal_probability?: number | null;
            /** Start Date */
            start_date?: string | null;
            /** Status */
            status?: string | null;
            /** Value */
            value?: number | null;
        };
        /** CsDashboardOut */
        CsDashboardOut: {
            /**
             * Active Accounts
             * @default 0
             */
            active_accounts: number;
            /**
             * At Risk Accounts
             * @default 0
             */
            at_risk_accounts: number;
            /** Avg Health Score */
            avg_health_score?: number | null;
            /**
             * Churned Accounts
             * @default 0
             */
            churned_accounts: number;
            /**
             * Expansion Accounts
             * @default 0
             */
            expansion_accounts: number;
            /**
             * Open Risks
             * @default 0
             */
            open_risks: number;
            /**
             * Open Tasks
             * @default 0
             */
            open_tasks: number;
            /**
             * Renewals Due 90D
             * @default 0
             */
            renewals_due_90d: number;
            /**
             * Total Accounts
             * @default 0
             */
            total_accounts: number;
            /**
             * Total Arr
             * @default 0
             */
            total_arr: number;
            /**
             * Total Mrr
             * @default 0
             */
            total_mrr: number;
            /**
             * Upcoming Meetings
             * @default 0
             */
            upcoming_meetings: number;
        };
        /** CsHealthScoreCreate */
        CsHealthScoreCreate: {
            /**
             * Detail
             * @default {}
             */
            detail: {
                [key: string]: unknown;
            };
            /**
             * Email Activity
             * @default 0
             */
            email_activity: number;
            /**
             * Executive Engagement
             * @default 0
             */
            executive_engagement: number;
            /**
             * Meeting Activity
             * @default 0
             */
            meeting_activity: number;
            /**
             * Open Issues
             * @default 100
             */
            open_issues: number;
            /**
             * Opportunity Activity
             * @default 0
             */
            opportunity_activity: number;
            /**
             * Product Adoption
             * @default 0
             */
            product_adoption: number;
            /**
             * Renewal Status
             * @default 100
             */
            renewal_status: number;
        };
        /** CsHealthScoreOut */
        CsHealthScoreOut: {
            /** Account Id */
            account_id: number;
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default {}
             */
            detail: {
                [key: string]: unknown;
            };
            /** Email Activity */
            email_activity: number;
            /** Executive Engagement */
            executive_engagement: number;
            /** Grade */
            grade: string;
            /** Id */
            id: number;
            /** Meeting Activity */
            meeting_activity: number;
            /** Open Issues */
            open_issues: number;
            /** Opportunity Activity */
            opportunity_activity: number;
            /** Product Adoption */
            product_adoption: number;
            /** Renewal Status */
            renewal_status: number;
            /** Score */
            score: number;
            /** Trend */
            trend: string;
        };
        /** CsLifecycleEventOut */
        CsLifecycleEventOut: {
            /** Account Id */
            account_id: number;
            /** Changed By */
            changed_by?: number | null;
            /** Created At */
            created_at?: string | null;
            /**
             * From Stage
             * @default
             */
            from_stage: string;
            /** Id */
            id: number;
            /**
             * Note
             * @default
             */
            note: string;
            /** Stage */
            stage: string;
        };
        /** CsMilestoneCreate */
        CsMilestoneCreate: {
            /** Account Id */
            account_id: number;
            /** Due Date */
            due_date?: string | null;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Plan Id */
            plan_id: number;
            /**
             * Status
             * @default pending
             */
            status: string;
        };
        /** CsMilestoneOut */
        CsMilestoneOut: {
            /** Account Id */
            account_id: number;
            /** Completed At */
            completed_at?: string | null;
            /** Created At */
            created_at?: string | null;
            /** Due Date */
            due_date?: string | null;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Plan Id */
            plan_id: number;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CsMilestonePatch */
        CsMilestonePatch: {
            /** Due Date */
            due_date?: string | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Status */
            status?: string | null;
        };
        /** CsRiskCreate */
        CsRiskCreate: {
            /** Account Id */
            account_id: number;
            /**
             * Description
             * @default
             */
            description: string;
            /** Due Date */
            due_date?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Severity
             * @default medium
             */
            severity: string;
            /**
             * Status
             * @default open
             */
            status: string;
            /** Title */
            title: string;
        };
        /** CsRiskOut */
        CsRiskOut: {
            /** Account Id */
            account_id: number;
            /** Created At */
            created_at?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Due Date */
            due_date?: string | null;
            /** Id */
            id: number;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Resolved At */
            resolved_at?: string | null;
            /** Severity */
            severity: string;
            /** Status */
            status: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CsRiskPatch */
        CsRiskPatch: {
            /** Description */
            description?: string | null;
            /** Due Date */
            due_date?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Severity */
            severity?: string | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /** CsSuccessPlanCreate */
        CsSuccessPlanCreate: {
            /** Account Id */
            account_id: number;
            /** Due Date */
            due_date?: string | null;
            /**
             * Goals
             * @default []
             */
            goals: {
                [key: string]: unknown;
            }[];
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Status
             * @default active
             */
            status: string;
        };
        /** CsSuccessPlanOut */
        CsSuccessPlanOut: {
            /** Account Id */
            account_id: number;
            /** Created At */
            created_at?: string | null;
            /** Due Date */
            due_date?: string | null;
            /**
             * Goals
             * @default []
             */
            goals: {
                [key: string]: unknown;
            }[];
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CsSuccessPlanPatch */
        CsSuccessPlanPatch: {
            /** Due Date */
            due_date?: string | null;
            /** Goals */
            goals?: {
                [key: string]: unknown;
            }[] | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Status */
            status?: string | null;
        };
        /** CsTimelineEvent */
        CsTimelineEvent: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Event Id */
            event_id: string;
            /** Event Type */
            event_type: string;
            /** Label */
            label: string;
            /**
             * Timestamp
             * Format: date-time
             */
            timestamp: string;
        };
        /** CustomDataJobOut */
        CustomDataJobOut: {
            /** Completed At */
            completed_at?: string | null;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Error Count
             * @default 0
             */
            error_count: number;
            /**
             * Errors
             * @default []
             */
            errors: unknown[];
            /** Id */
            id: number;
            /** Job Type */
            job_type: string;
            /** Object Id */
            object_id: number;
            /** Status */
            status: string;
            /**
             * Success Count
             * @default 0
             */
            success_count: number;
            /**
             * Total Rows
             * @default 0
             */
            total_rows: number;
        };
        /** CustomFieldCreate */
        CustomFieldCreate: {
            /** Api Name */
            api_name: string;
            /** Default Value */
            default_value?: unknown;
            /**
             * Display Order
             * @default 0
             */
            display_order: number;
            /** Field Type */
            field_type: string;
            /**
             * Is Required
             * @default false
             */
            is_required: boolean;
            /** Lookup Object Id */
            lookup_object_id?: number | null;
            /** Name */
            name: string;
            /**
             * Picklist Options
             * @default []
             */
            picklist_options: string[];
            /**
             * Validation
             * @default {}
             */
            validation: {
                [key: string]: unknown;
            };
        };
        /** CustomFieldOut */
        CustomFieldOut: {
            /** Api Name */
            api_name: string;
            /** Created At */
            created_at?: string | null;
            /** Default Value */
            default_value?: unknown;
            /**
             * Display Order
             * @default 0
             */
            display_order: number;
            /** Field Type */
            field_type: string;
            /** Id */
            id: number;
            /**
             * Is Required
             * @default false
             */
            is_required: boolean;
            /** Lookup Object Id */
            lookup_object_id?: number | null;
            /** Name */
            name: string;
            /** Object Id */
            object_id: number;
            /**
             * Picklist Options
             * @default []
             */
            picklist_options: string[];
            /** Updated At */
            updated_at?: string | null;
            /**
             * Validation
             * @default {}
             */
            validation: {
                [key: string]: unknown;
            };
        };
        /** CustomFieldPatch */
        CustomFieldPatch: {
            /** Default Value */
            default_value?: unknown;
            /** Display Order */
            display_order?: number | null;
            /** Is Required */
            is_required?: boolean | null;
            /** Name */
            name?: string | null;
            /** Picklist Options */
            picklist_options?: string[] | null;
            /** Validation */
            validation?: {
                [key: string]: unknown;
            } | null;
        };
        /** CustomFormCreate */
        CustomFormCreate: {
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Is Default
             * @default false
             */
            is_default: boolean;
            /**
             * @default {
             *       "sections": []
             *     }
             */
            layout: components["schemas"]["CustomFormLayout"];
            /** Name */
            name: string;
        };
        /** CustomFormFieldLayout */
        CustomFormFieldLayout: {
            /** Field Api Name */
            field_api_name: string;
            /**
             * Read Only
             * @default false
             */
            read_only: boolean;
            /** Required Override */
            required_override?: boolean | null;
            /** Visible If */
            visible_if?: {
                [key: string]: unknown;
            } | null;
        };
        /** CustomFormLayout */
        CustomFormLayout: {
            /**
             * Sections
             * @default []
             */
            sections: components["schemas"]["CustomFormSection"][];
        };
        /** CustomFormOut */
        CustomFormOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /**
             * Is Default
             * @default false
             */
            is_default: boolean;
            /**
             * Layout
             * @default {}
             */
            layout: {
                [key: string]: unknown;
            };
            /** Name */
            name: string;
            /** Object Id */
            object_id: number;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CustomFormPatch */
        CustomFormPatch: {
            /** Description */
            description?: string | null;
            /** Is Default */
            is_default?: boolean | null;
            layout?: components["schemas"]["CustomFormLayout"] | null;
            /** Name */
            name?: string | null;
        };
        /** CustomFormSection */
        CustomFormSection: {
            /**
             * Fields
             * @default []
             */
            fields: components["schemas"]["CustomFormFieldLayout"][];
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** CustomObjectAnalyticsOut */
        CustomObjectAnalyticsOut: {
            /**
             * Export Count
             * @default 0
             */
            export_count: number;
            /**
             * Field Utilization
             * @default []
             */
            field_utilization: components["schemas"]["FieldUtilizationOut"][];
            /**
             * Import Success Rate
             * @default 0
             */
            import_success_rate: number;
            /** Object Id */
            object_id: number;
            /**
             * Records Created By Period
             * @default {}
             */
            records_created_by_period: {
                [key: string]: number;
            };
            /**
             * Records Created Total
             * @default 0
             */
            records_created_total: number;
            /**
             * Records Updated Total
             * @default 0
             */
            records_updated_total: number;
        };
        /** CustomObjectCreate */
        CustomObjectCreate: {
            /** Api Name */
            api_name: string;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Icon
             * @default
             */
            icon: string;
            /** Name */
            name: string;
            /**
             * Status
             * @default draft
             */
            status: string;
        };
        /** CustomObjectDashboardOut */
        CustomObjectDashboardOut: {
            /**
             * Active Objects
             * @default 0
             */
            active_objects: number;
            /**
             * Import Jobs Run
             * @default 0
             */
            import_jobs_run: number;
            /**
             * Recent Import Errors
             * @default 0
             */
            recent_import_errors: number;
            /**
             * Recent Records
             * @default []
             */
            recent_records: components["schemas"]["CustomRecordOut"][];
            /**
             * Total Objects
             * @default 0
             */
            total_objects: number;
            /**
             * Total Records
             * @default 0
             */
            total_records: number;
        };
        /** CustomObjectOut */
        CustomObjectOut: {
            /** Api Name */
            api_name: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Icon
             * @default
             */
            icon: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1
             */
            version: number;
        };
        /** CustomObjectPatch */
        CustomObjectPatch: {
            /** Description */
            description?: string | null;
            /** Icon */
            icon?: string | null;
            /** Name */
            name?: string | null;
            /** Status */
            status?: string | null;
        };
        /** CustomRecordAuditOut */
        CustomRecordAuditOut: {
            /** Action */
            action: string;
            /** Changed By */
            changed_by?: number | null;
            /**
             * Changed By Email
             * @default
             */
            changed_by_email: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Field Changes
             * @default {}
             */
            field_changes: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /** Record Id */
            record_id: number;
        };
        /** CustomRecordCreate */
        CustomRecordCreate: {
            /**
             * Data
             * @default {}
             */
            data: {
                [key: string]: unknown;
            };
        };
        /** CustomRecordOut */
        CustomRecordOut: {
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Data
             * @default {}
             */
            data: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /** Object Id */
            object_id: number;
            /** Updated At */
            updated_at?: string | null;
            /** Updated By */
            updated_by?: number | null;
        };
        /** CustomRecordPatch */
        CustomRecordPatch: {
            /**
             * Data
             * @default {}
             */
            data: {
                [key: string]: unknown;
            };
        };
        /** CustomReportCreate */
        CustomReportCreate: {
            /** Entity Type */
            entity_type: string;
            /**
             * Filters
             * @default {}
             */
            filters: {
                [key: string]: unknown;
            };
            /**
             * Group By
             * @default
             */
            group_by: string;
            /** Name */
            name: string;
        };
        /** CustomReportOut */
        CustomReportOut: {
            /** Created At */
            created_at?: string | null;
            /** Entity Type */
            entity_type: string;
            /**
             * Filters
             * @default {}
             */
            filters: {
                [key: string]: unknown;
            };
            /**
             * Group By
             * @default
             */
            group_by: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CustomReportPatch */
        CustomReportPatch: {
            /** Filters */
            filters?: {
                [key: string]: unknown;
            } | null;
            /** Group By */
            group_by?: string | null;
            /** Name */
            name?: string | null;
            /** Status */
            status?: string | null;
        };
        /** CustomReportResultOut */
        CustomReportResultOut: {
            /**
             * Columns
             * @default []
             */
            columns: string[];
            /** Report Id */
            report_id: number;
            /**
             * Rows
             * @default []
             */
            rows: {
                [key: string]: unknown;
            }[];
            /**
             * Total Rows
             * @default 0
             */
            total_rows: number;
        };
        /** DatasetBuildResult */
        DatasetBuildResult: {
            /** Columns */
            columns: string[];
            /** Feature Version */
            feature_version: string;
            /** Negative */
            negative: number;
            /** Positive */
            positive: number;
            /** Row Count */
            row_count: number;
            /** Version */
            version: string;
            /** Window Days */
            window_days: number;
        };
        /** DealAnalyticsOut */
        DealAnalyticsOut: {
            /**
             * Loss Rate
             * @default 0
             */
            loss_rate: number;
            /**
             * Lost Deals
             * @default 0
             */
            lost_deals: number;
            /**
             * Open Deals
             * @default 0
             */
            open_deals: number;
            /** Pipeline Id */
            pipeline_id: number;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /**
             * Stage Velocity
             * @default []
             */
            stage_velocity: components["schemas"]["StageVelocityOut"][];
            /**
             * Stalled Deal Count
             * @default 0
             */
            stalled_deal_count: number;
            /**
             * Total Deals
             * @default 0
             */
            total_deals: number;
            /**
             * Weighted Pipeline
             * @default 0
             */
            weighted_pipeline: number;
            /**
             * Win Rate
             * @default 0
             */
            win_rate: number;
            /**
             * Won Deals
             * @default 0
             */
            won_deals: number;
        };
        /** DealCreate */
        DealCreate: {
            /** Company Domain */
            company_domain: string;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** Expected Close Date */
            expected_close_date?: string | null;
            /**
             * Forecast Category
             * @default pipeline
             */
            forecast_category: string;
            /**
             * Lost Reason
             * @default
             */
            lost_reason: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Opportunity Id */
            opportunity_id?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Pipeline Id */
            pipeline_id: number;
            /** Probability */
            probability?: number | null;
            /** Stage Id */
            stage_id: number;
            /**
             * Tags
             * @default []
             */
            tags: unknown[];
            /** Title */
            title: string;
            /** Value */
            value?: number | null;
            /**
             * Won Reason
             * @default
             */
            won_reason: string;
        };
        /** DealDashboardOut */
        DealDashboardOut: {
            /**
             * Closing Soon
             * @default []
             */
            closing_soon: components["schemas"]["DealOut"][];
            /**
             * High Value Deals
             * @default []
             */
            high_value_deals: components["schemas"]["DealOut"][];
            /** Pipeline Id */
            pipeline_id?: number | null;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /**
             * Recently Lost
             * @default []
             */
            recently_lost: components["schemas"]["DealOut"][];
            /**
             * Recently Won
             * @default []
             */
            recently_won: components["schemas"]["DealOut"][];
            /**
             * Stalled Deals
             * @default []
             */
            stalled_deals: components["schemas"]["DealOut"][];
            /**
             * Total Lost Deals
             * @default 0
             */
            total_lost_deals: number;
            /**
             * Total Open Deals
             * @default 0
             */
            total_open_deals: number;
            /**
             * Total Won Deals
             * @default 0
             */
            total_won_deals: number;
            /**
             * Weighted Pipeline
             * @default 0
             */
            weighted_pipeline: number;
            /**
             * Win Rate
             * @default 0
             */
            win_rate: number;
        };
        /** DealIntelligenceOut */
        DealIntelligenceOut: {
            /**
             * Backup Contacts
             * @default []
             */
            backup_contacts: components["schemas"]["ContactRecommendationOut"][];
            best_contact?: components["schemas"]["ContactRecommendationOut"] | null;
            buying_committee?: components["schemas"]["BuyingCommitteeOut"] | null;
            /** Company Domain */
            company_domain: string;
            /** Deal Id */
            deal_id: number;
            next_action?: components["schemas"]["NextActionOut"] | null;
            outreach_priority?: components["schemas"]["OutreachPriorityOut"] | null;
            /**
             * Recommended Sequence
             * @default []
             */
            recommended_sequence: components["schemas"]["SequenceStepOut"][];
            /**
             * Relationship Strength
             * @default 0
             */
            relationship_strength: number;
            success_probability?: components["schemas"]["SuccessProbabilityOut"] | null;
        };
        /** DealMoveIn */
        DealMoveIn: {
            /** Stage Id */
            stage_id: number;
        };
        /** DealOut */
        DealOut: {
            /** Company Domain */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** Expected Close Date */
            expected_close_date?: string | null;
            /**
             * Forecast Category
             * @default pipeline
             */
            forecast_category: string;
            /** Id */
            id: number;
            /** Last Activity At */
            last_activity_at?: string | null;
            /**
             * Lost Reason
             * @default
             */
            lost_reason: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Opportunity Id */
            opportunity_id?: string | null;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Pipeline Id */
            pipeline_id: number;
            /**
             * Probability
             * @default 0
             */
            probability: number;
            /** Stage Id */
            stage_id: number;
            /**
             * Stage Name
             * @default
             */
            stage_name: string;
            /**
             * Tags
             * @default []
             */
            tags: unknown[];
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
            /** Value */
            value?: number | null;
            /**
             * Won Reason
             * @default
             */
            won_reason: string;
        };
        /** DealPatch */
        DealPatch: {
            /** Currency */
            currency?: string | null;
            /** Expected Close Date */
            expected_close_date?: string | null;
            /** Forecast Category */
            forecast_category?: string | null;
            /** Lost Reason */
            lost_reason?: string | null;
            /** Notes */
            notes?: string | null;
            /** Opportunity Id */
            opportunity_id?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Probability */
            probability?: number | null;
            /** Tags */
            tags?: unknown[] | null;
            /** Title */
            title?: string | null;
            /** Value */
            value?: number | null;
            /** Won Reason */
            won_reason?: string | null;
        };
        /** DealStageHistoryOut */
        DealStageHistoryOut: {
            /** Changed By */
            changed_by?: number | null;
            /** Created At */
            created_at?: string | null;
            /** Deal Id */
            deal_id: number;
            /** Entered At */
            entered_at?: string | null;
            /** Exited At */
            exited_at?: string | null;
            /** From Stage Id */
            from_stage_id?: number | null;
            /** Id */
            id: number;
            /** Time In Stage Seconds */
            time_in_stage_seconds?: number | null;
            /** To Stage Id */
            to_stage_id: number;
        };
        /** DecisionMakerCompanies */
        DecisionMakerCompanies: {
            /** Companies */
            companies: components["schemas"]["DecisionMakerCompany"][];
            /**
             * Unresolved
             * @default 0
             */
            unresolved: number;
        };
        /**
         * DecisionMakerCompany
         * @description A company with its resolved decision-maker count (company-first directory).
         */
        DecisionMakerCompany: {
            /** Company Domain */
            company_domain: string;
            /** Company Name */
            company_name: string;
            /**
             * Senior
             * @default 0
             */
            senior: number;
            /** Total */
            total: number;
        };
        /**
         * DecisionMakerDetailOut
         * @description Full enrichment for ONE decision maker (lazy-loaded by the profile panel).
         *
         *     Everything in :class:`DecisionMakerOut` plus the heavier/rarer fields read from
         *     the raw Apify record in ``profile_data`` — kept off the list payload so the
         *     directory and Company Profile stay fast. All optional: missing → None/blank.
         */
        DecisionMakerDetailOut: {
            /** Agent Score */
            agent_score?: number | null;
            /** Alt Emails */
            alt_emails?: string | null;
            /** Apify Person Id */
            apify_person_id?: string | null;
            /** Business Unit */
            business_unit?: string | null;
            /** Captured At */
            captured_at?: string | null;
            /** City */
            city?: string | null;
            /** Company Domain */
            company_domain?: string | null;
            /** Company Size */
            company_size?: string | null;
            /**
             * Confidence Factors
             * @default []
             */
            confidence_factors: string[];
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /** Confidence Score */
            confidence_score?: number | null;
            /** Connections */
            connections?: string | null;
            /** Country */
            country?: string | null;
            /**
             * Current Title
             * @default
             */
            current_title: string;
            /** Department */
            department?: string | null;
            /** Department Class */
            department_class?: string | null;
            /** Department Group */
            department_group?: string | null;
            /** Email Status */
            email_status?: string | null;
            /** Engineering Relevance */
            engineering_relevance?: number | null;
            /** Exec Level */
            exec_level?: string | null;
            /**
             * First Name
             * @default
             */
            first_name: string;
            follow_up?: components["schemas"]["FollowUpOut"] | null;
            /** Followers */
            followers?: string | null;
            /** Full Name */
            full_name?: string | null;
            /** Functional Area */
            functional_area?: string | null;
            /**
             * Headline
             * @default
             */
            headline: string;
            /** Hierarchy Rank */
            hierarchy_rank?: number | null;
            /** Id */
            id: number;
            /** Industry */
            industry?: string | null;
            /**
             * Influence Factors
             * @default []
             */
            influence_factors: string[];
            /** Influence Raw */
            influence_raw?: number | null;
            /** Influence Score */
            influence_score?: number | null;
            /** Ingested At */
            ingested_at?: string | null;
            /** Languages */
            languages?: string | null;
            /**
             * Last Name
             * @default
             */
            last_name: string;
            /**
             * Leadership Signals
             * @default []
             */
            leadership_signals: components["schemas"]["LeadershipSignalOut"][];
            /** Linkedin Url */
            linkedin_url: string;
            /**
             * Location
             * @default
             */
            location: string;
            /**
             * Match Score
             * @default 0
             */
            match_score: number;
            next_action?: components["schemas"]["NextActionOut"] | null;
            /** Organization Linkedin */
            organization_linkedin?: string | null;
            /** Organization Website */
            organization_website?: string | null;
            /** Photo Url */
            photo_url?: string | null;
            /** Relationship Score */
            relationship_score?: number | null;
            /**
             * Relationship Status
             * @default
             */
            relationship_status: string;
            /**
             * Resolved Company Name
             * @default
             */
            resolved_company_name: string;
            /**
             * Risk Flags
             * @default []
             */
            risk_flags: string[];
            /**
             * Risk Severity
             * @default
             */
            risk_severity: string;
            /**
             * Seniority
             * @default
             */
            seniority: string;
            /** Skills */
            skills?: string | null;
            /**
             * Source
             * @default
             */
            source: string;
            /** State Region */
            state_region?: string | null;
            /**
             * Status
             * @default
             */
            status: string;
            /** Summary */
            summary?: string | null;
            /** Work Email */
            work_email?: string | null;
            /** Work Phone */
            work_phone?: string | null;
            /** Years In Company */
            years_in_company?: string | null;
            /** Years In Role */
            years_in_role?: string | null;
        };
        /**
         * DecisionMakerNoteIn
         * @description Create a collaboration note. Tier rules (enforced in the service):
         *     ``admin`` → admins only · ``manager`` → admin/manager · ``team`` & ``personal``
         *     → any authenticated user (``personal`` is private to its author).
         */
        DecisionMakerNoteIn: {
            /**
             * Content
             * @default
             */
            content: string;
            /**
             * Note Type
             * @default personal
             * @enum {string}
             */
            note_type: "admin" | "manager" | "team" | "personal";
        };
        /** DecisionMakerNoteOut */
        DecisionMakerNoteOut: {
            /**
             * Author Email
             * @default
             */
            author_email: string;
            /**
             * Author Role
             * @default
             */
            author_role: string;
            /**
             * Can Edit
             * @default false
             */
            can_edit: boolean;
            /**
             * Content
             * @default
             */
            content: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /** Decision Maker Id */
            decision_maker_id: number;
            /** Id */
            id: number;
            /** Note Type */
            note_type: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** DecisionMakerNoteUpdate */
        DecisionMakerNoteUpdate: {
            /** Content */
            content: string;
        };
        /** DecisionMakerOut */
        DecisionMakerOut: {
            /** Agent Score */
            agent_score?: number | null;
            /** Alt Emails */
            alt_emails?: string | null;
            /** City */
            city?: string | null;
            /** Company Domain */
            company_domain?: string | null;
            /** Company Size */
            company_size?: string | null;
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /** Confidence Score */
            confidence_score?: number | null;
            /** Country */
            country?: string | null;
            /**
             * Current Title
             * @default
             */
            current_title: string;
            /** Department Class */
            department_class?: string | null;
            /** Department Group */
            department_group?: string | null;
            /** Email Status */
            email_status?: string | null;
            /** Exec Level */
            exec_level?: string | null;
            /**
             * First Name
             * @default
             */
            first_name: string;
            /** Full Name */
            full_name?: string | null;
            /** Functional Area */
            functional_area?: string | null;
            /**
             * Headline
             * @default
             */
            headline: string;
            /** Id */
            id: number;
            /** Industry */
            industry?: string | null;
            /** Influence Score */
            influence_score?: number | null;
            /**
             * Last Name
             * @default
             */
            last_name: string;
            /** Linkedin Url */
            linkedin_url: string;
            /**
             * Location
             * @default
             */
            location: string;
            /**
             * Match Score
             * @default 0
             */
            match_score: number;
            /** Organization Linkedin */
            organization_linkedin?: string | null;
            /** Organization Website */
            organization_website?: string | null;
            /** Photo Url */
            photo_url?: string | null;
            /**
             * Resolved Company Name
             * @default
             */
            resolved_company_name: string;
            /**
             * Seniority
             * @default
             */
            seniority: string;
            /** State Region */
            state_region?: string | null;
            /**
             * Status
             * @default
             */
            status: string;
            /** Work Email */
            work_email?: string | null;
            /** Work Phone */
            work_phone?: string | null;
        };
        /** DemandSignalOut */
        DemandSignalOut: {
            /**
             * Ats Provider
             * @default
             */
            ats_provider: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Demand Score
             * @default 0
             */
            demand_score: number;
            /**
             * Hiring Trend
             * @default
             */
            hiring_trend: string;
            /**
             * India Hiring Flag
             * @default false
             */
            india_hiring_flag: boolean;
            /**
             * Lead Readiness Score
             * @default 0
             */
            lead_readiness_score: number;
            /**
             * Newest Job Date
             * @default
             */
            newest_job_date: string;
            /**
             * Normalized Demand Score
             * @default 0
             */
            normalized_demand_score: number;
            /**
             * Primary Focus
             * @default
             */
            primary_focus: string;
            /**
             * Technologies Detected
             * @default
             */
            technologies_detected: string;
            /**
             * Total Engineering Jobs
             * @default 0
             */
            total_engineering_jobs: number;
        };
        /** DepartmentCoverageOut */
        DepartmentCoverageOut: {
            /**
             * Coverage Pct
             * @default 0
             */
            coverage_pct: number;
            /**
             * Missing
             * @default []
             */
            missing: string[];
            /**
             * Present
             * @default 0
             */
            present: number;
            /**
             * Rows
             * @default []
             */
            rows: components["schemas"]["DeptCoverageRowOut"][];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** DeptCoverageRowOut */
        DeptCoverageRowOut: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Department */
            department: string;
            /**
             * Present
             * @default false
             */
            present: boolean;
        };
        /** EmailAttachmentIn */
        EmailAttachmentIn: {
            /** Content B64 */
            content_b64: string;
            /**
             * Content Type
             * @default application/octet-stream
             */
            content_type: string;
            /** Filename */
            filename: string;
        };
        /** EmailAttachmentOut */
        EmailAttachmentOut: {
            /**
             * Content Type
             * @default application/octet-stream
             */
            content_type: string;
            /** Created At */
            created_at?: string | null;
            /** Filename */
            filename: string;
            /** Id */
            id: number;
            /** Outreach Message Id */
            outreach_message_id: number;
            /**
             * Size Bytes
             * @default 0
             */
            size_bytes: number;
            /**
             * Status
             * @default uploaded
             */
            status: string;
        };
        /** EmailConversationOut */
        EmailConversationOut: {
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Created At */
            created_at?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Folder
             * @default inbox
             */
            folder: string;
            /** Id */
            id: number;
            /**
             * Is Archived
             * @default false
             */
            is_archived: boolean;
            /**
             * Is Pinned
             * @default false
             */
            is_pinned: boolean;
            /**
             * Is Starred
             * @default false
             */
            is_starred: boolean;
            /**
             * Is Trashed
             * @default false
             */
            is_trashed: boolean;
            /**
             * Labels
             * @default []
             */
            labels: components["schemas"]["EmailLabelOut"][];
            /** Last Message At */
            last_message_at?: string | null;
            /**
             * Message Count
             * @default 0
             */
            message_count: number;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /**
             * Preview Text
             * @default
             */
            preview_text: string;
            /**
             * Subject
             * @default
             */
            subject: string;
            /**
             * Thread Id
             * @default
             */
            thread_id: string;
            /**
             * Unread Count
             * @default 0
             */
            unread_count: number;
            /** Updated At */
            updated_at?: string | null;
        };
        /** EmailLabelIn */
        EmailLabelIn: {
            /**
             * Color
             * @default gray
             */
            color: string;
            /** Name */
            name: string;
        };
        /** EmailLabelOut */
        EmailLabelOut: {
            /**
             * Color
             * @default gray
             */
            color: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /** Id */
            id: number;
            /**
             * Is System
             * @default false
             */
            is_system: boolean;
            /** Name */
            name: string;
        };
        /** EmailProviderAccountIn */
        EmailProviderAccountIn: {
            /** Config Json */
            config_json?: string | null;
            /**
             * Provider Type
             * @default mock
             */
            provider_type: string;
        };
        /** EmailProviderAccountOut */
        EmailProviderAccountOut: {
            /**
             * Connection Status
             * @default connected
             */
            connection_status: string;
            /**
             * Email Address
             * @default
             */
            email_address: string;
            /**
             * Error Message
             * @default
             */
            error_message: string;
            /**
             * Id
             * @default 0
             */
            id: number;
            /** Last Sync At */
            last_sync_at?: string | null;
            /**
             * Provider Type
             * @default mock
             */
            provider_type: string;
            /**
             * Sync Error
             * @default
             */
            sync_error: string;
            /**
             * Sync Status
             * @default idle
             */
            sync_status: string;
            /** Token Expires At */
            token_expires_at?: string | null;
            /** Updated At */
            updated_at?: string | null;
            /** User Id */
            user_id?: number | null;
        };
        /** EmailSchedulerTickOut */
        EmailSchedulerTickOut: {
            /**
             * Cancelled By Deadline
             * @default 0
             */
            cancelled_by_deadline: number;
            /**
             * Gmail Synced
             * @default 0
             */
            gmail_synced: number;
            /**
             * Gmail Tokens Refreshed
             * @default 0
             */
            gmail_tokens_refreshed: number;
            /**
             * Scheduled To Queued
             * @default 0
             */
            scheduled_to_queued: number;
            /**
             * Sequences Advanced
             * @default 0
             */
            sequences_advanced: number;
            /**
             * Timestamp
             * Format: date-time
             */
            timestamp: string;
        };
        /**
         * EngagementOut
         * @description A per-company sales-pitch / engagement recommendation (P-task 9): a likely
         *     business need, the matching Silicon Patterns offering, a one-line pitch, a
         *     confidence score, and the rationale (evidence) that produced it.
         */
        EngagementOut: {
            /**
             * Business Need
             * @default
             */
            business_need: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Confidence
             * @default 0
             */
            confidence: number;
            /**
             * Confidence Label
             * @default low
             */
            confidence_label: string;
            /**
             * Model Version
             * @default
             */
            model_version: string;
            /**
             * Offering
             * @default
             */
            offering: string;
            /**
             * Pitch
             * @default
             */
            pitch: string;
            /**
             * Rationale
             * @default []
             */
            rationale: string[];
            /**
             * Signals Used
             * @default 0
             */
            signals_used: number;
        };
        /** EngagementScoreOut */
        EngagementScoreOut: {
            /**
             * Factors
             * @default []
             */
            factors: string[];
            /**
             * Label
             * @default Dormant
             */
            label: string;
            /**
             * Relationship
             * @default Cold
             */
            relationship: string;
            /**
             * Score
             * @default 0
             */
            score: number;
        };
        /** EventPublishIn */
        EventPublishIn: {
            /** Category */
            category: string;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Event Type */
            event_type: string;
            /**
             * Payload
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
        };
        /** ExecutionOut */
        ExecutionOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Duration Ms
             * @default 0
             */
            duration_ms: number;
            /**
             * Failure Count
             * @default 0
             */
            failure_count: number;
            /** Finished At */
            finished_at?: string | null;
            /** Id */
            id: number;
            /**
             * Notification Detail
             * @default
             */
            notification_detail: string;
            /**
             * Notification Status
             * @default pending
             */
            notification_status: string;
            /**
             * Notified Count
             * @default 0
             */
            notified_count: number;
            /**
             * Records Processed
             * @default 0
             */
            records_processed: number;
            /** Run Id */
            run_id: string;
            /** Scheduled Slot */
            scheduled_slot?: string | null;
            /**
             * Stages
             * @default []
             */
            stages: components["schemas"]["ExecutionStageOut"][];
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /**
             * Totals
             * @default {}
             */
            totals: {
                [key: string]: number;
            };
            /** Trigger */
            trigger: string;
            /**
             * Warning Count
             * @default 0
             */
            warning_count: number;
        };
        /** ExecutionStageOut */
        ExecutionStageOut: {
            /** Component */
            component: string;
            /**
             * Created
             * @default 0
             */
            created: number;
            /**
             * Duration Ms
             * @default 0
             */
            duration_ms: number;
            /**
             * Errors
             * @default []
             */
            errors: string[];
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Processed
             * @default 0
             */
            processed: number;
            /**
             * Review
             * @default 0
             */
            review: number;
            /**
             * Status
             * @default
             */
            status: string;
            /**
             * Updated
             * @default 0
             */
            updated: number;
        };
        /** ExecutiveDashboardOut */
        ExecutiveDashboardOut: {
            /**
             * Active Customers
             * @default 0
             */
            active_customers: number;
            /**
             * Arr
             * @default 0
             */
            arr: number;
            /** Avg Sales Cycle Days */
            avg_sales_cycle_days?: number | null;
            /**
             * Churn Rate
             * @default 0
             */
            churn_rate: number;
            /**
             * Conversion Rate
             * @default 0
             */
            conversion_rate: number;
            /**
             * Expansion Accounts
             * @default 0
             */
            expansion_accounts: number;
            /** Generated At */
            generated_at?: string | null;
            /**
             * Mrr
             * @default 0
             */
            mrr: number;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /**
             * Revenue Ttm
             * @default 0
             */
            revenue_ttm: number;
            /** Sales Velocity */
            sales_velocity?: number | null;
            /**
             * Weighted Forecast
             * @default 0
             */
            weighted_forecast: number;
            /**
             * Win Rate
             * @default 0
             */
            win_rate: number;
        };
        /** ExecutiveReportOut */
        ExecutiveReportOut: {
            /**
             * Data
             * @default {}
             */
            data: {
                [key: string]: unknown;
            };
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Report Type */
            report_type: string;
        };
        /** FeatureRefreshResult */
        FeatureRefreshResult: {
            /** Computed */
            computed: number;
            /** Feature Version */
            feature_version: string;
            /** Reused */
            reused: number;
            /** Total */
            total: number;
        };
        /** FeatureVectorOut */
        FeatureVectorOut: {
            /** Entity Id */
            entity_id: string;
            /**
             * Entity Type
             * @default company
             */
            entity_type: string;
            /** Feature Version */
            feature_version: string;
            /** Features */
            features: {
                [key: string]: unknown;
            };
        };
        /** FieldUtilizationOut */
        FieldUtilizationOut: {
            /** Field Api Name */
            field_api_name: string;
            /**
             * Filled Pct
             * @default 0
             */
            filled_pct: number;
        };
        /** FollowUpOut */
        FollowUpOut: {
            /** Days Since Last Contact */
            days_since_last_contact?: number | null;
            /** Next Followup At */
            next_followup_at?: string | null;
            /**
             * Overdue
             * @default false
             */
            overdue: boolean;
            /**
             * Reason
             * @default
             */
            reason: string;
            /**
             * Reminder Priority
             * @default low
             */
            reminder_priority: string;
        };
        /** ForecastAccuracyOut */
        ForecastAccuracyOut: {
            /**
             * Accuracy Pct
             * @default 0
             */
            accuracy_pct: number;
            /**
             * Actual Amount
             * @default 0
             */
            actual_amount: number;
            /** Category */
            category: string;
            /**
             * Forecasted Amount
             * @default 0
             */
            forecasted_amount: number;
            /** Period Key */
            period_key: string;
            /** Period Type */
            period_type: string;
            /** Pipeline Id */
            pipeline_id?: number | null;
            /** Snapshot Id */
            snapshot_id: number;
            /**
             * Variance
             * @default 0
             */
            variance: number;
        };
        /** ForecastByOwnerOut */
        ForecastByOwnerOut: {
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id: number;
            /**
             * Weighted Value
             * @default 0
             */
            weighted_value: number;
        };
        /** ForecastByQuarterOut */
        ForecastByQuarterOut: {
            /** Quarter */
            quarter: string;
            /**
             * Weighted Value
             * @default 0
             */
            weighted_value: number;
        };
        /** ForecastOut */
        ForecastOut: {
            /**
             * Avg Deal Size
             * @default 0
             */
            avg_deal_size: number;
            /** Avg Sales Cycle Days */
            avg_sales_cycle_days?: number | null;
            /**
             * Expected Revenue
             * @default 0
             */
            expected_revenue: number;
            /**
             * Forecast By Owner
             * @default []
             */
            forecast_by_owner: components["schemas"]["ForecastByOwnerOut"][];
            /**
             * Forecast By Quarter
             * @default []
             */
            forecast_by_quarter: components["schemas"]["ForecastByQuarterOut"][];
            /**
             * Lost Deals
             * @default 0
             */
            lost_deals: number;
            /**
             * Open Deals
             * @default 0
             */
            open_deals: number;
            /** Pipeline Id */
            pipeline_id: number;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /** Pipeline Velocity */
            pipeline_velocity?: number | null;
            /**
             * Weighted Pipeline
             * @default 0
             */
            weighted_pipeline: number;
            /**
             * Win Probability
             * @default 0
             */
            win_probability: number;
            /**
             * Won Deals
             * @default 0
             */
            won_deals: number;
        };
        /** ForecastPeriodOut */
        ForecastPeriodOut: {
            /**
             * Best Case Value
             * @default 0
             */
            best_case_value: number;
            /**
             * Commit Value
             * @default 0
             */
            commit_value: number;
            /**
             * Deal Count
             * @default 0
             */
            deal_count: number;
            /** Period Key */
            period_key: string;
            /** Period Type */
            period_type: string;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /**
             * Weighted Value
             * @default 0
             */
            weighted_value: number;
        };
        /** ForecastSnapshotOut */
        ForecastSnapshotOut: {
            /** Category */
            category: string;
            /**
             * Forecasted Amount
             * @default 0
             */
            forecasted_amount: number;
            /** Id */
            id: number;
            /** Period Key */
            period_key: string;
            /** Period Type */
            period_type: string;
            /** Pipeline Id */
            pipeline_id?: number | null;
            /** Snapshot At */
            snapshot_at?: string | null;
        };
        /** FunnelAnalyticsOut */
        FunnelAnalyticsOut: {
            /**
             * Campaign Funnel
             * @default []
             */
            campaign_funnel: components["schemas"]["FunnelStageOut"][];
            /**
             * Deal Funnel
             * @default []
             */
            deal_funnel: components["schemas"]["FunnelStageOut"][];
            /**
             * Lead Funnel
             * @default []
             */
            lead_funnel: components["schemas"]["FunnelStageOut"][];
            /**
             * Opportunity Funnel
             * @default []
             */
            opportunity_funnel: components["schemas"]["FunnelStageOut"][];
        };
        /** FunnelStageOut */
        FunnelStageOut: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Drop Off Pct */
            drop_off_pct?: number | null;
            /** Stage */
            stage: string;
        };
        /** GmailAuthUrlOut */
        GmailAuthUrlOut: {
            /** Auth Url */
            auth_url: string;
            /** State */
            state: string;
        };
        /** GmailConnectOut */
        GmailConnectOut: {
            /**
             * Connection Status
             * @default connected
             */
            connection_status: string;
            /**
             * Email Address
             * @default
             */
            email_address: string;
            /**
             * Id
             * @default 0
             */
            id: number;
            /**
             * Provider Type
             * @default gmail
             */
            provider_type: string;
            /**
             * Sync Status
             * @default idle
             */
            sync_status: string;
            /** Token Expires At */
            token_expires_at?: string | null;
        };
        /** GmailRefreshOut */
        GmailRefreshOut: {
            /**
             * Error
             * @default
             */
            error: string;
            /** Refreshed */
            refreshed: boolean;
            /** Token Expires At */
            token_expires_at?: string | null;
        };
        /** GmailSyncResultOut */
        GmailSyncResultOut: {
            /**
             * Accounts Synced
             * @default 0
             */
            accounts_synced: number;
            /**
             * Error
             * @default
             */
            error: string;
            /**
             * Ingested
             * @default 0
             */
            ingested: number;
            /**
             * Next Cursor
             * @default
             */
            next_cursor: string;
            /**
             * Skipped
             * @default 0
             */
            skipped: number;
        };
        /** GraphEdgeOut */
        GraphEdgeOut: {
            /**
             * Kind
             * @default
             */
            kind: string;
            /** Source */
            source: string;
            /** Target */
            target: string;
        };
        /** GraphNodeOut */
        GraphNodeOut: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Dm Id */
            dm_id?: number | null;
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Score */
            score?: number | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthOut */
        HealthOut: {
            /** App */
            app: string;
            /** Database */
            database: string;
            /** Status */
            status: string;
            /** Version */
            version: string;
        };
        /** HeatmapRowOut */
        HeatmapRowOut: {
            /**
             * Contacts
             * @default 0
             */
            contacts: number;
            /** Department */
            department: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Status
             * @default Missing
             */
            status: string;
        };
        /**
         * HierarchyLevelOut
         * @description One organisation-hierarchy tier (Founder/CEO → IC), with its contacts.
         */
        HierarchyLevelOut: {
            /**
             * Contacts
             * @default []
             */
            contacts: components["schemas"]["RankedContactOut"][];
            /** Level */
            level: string;
            /** Rank */
            rank: number;
        };
        /** InferenceResultOut */
        InferenceResultOut: {
            /** Batches */
            batches: number;
            /** Model Version */
            model_version: string;
            /** Scored */
            scored: number;
        };
        /** IntegrationAnalyticsOut */
        IntegrationAnalyticsOut: {
            /**
             * Api Requests Total
             * @default 0
             */
            api_requests_total: number;
            /**
             * Connector Usage
             * @default {}
             */
            connector_usage: {
                [key: string]: number;
            };
            /**
             * Integration Health
             * @default {}
             */
            integration_health: {
                [key: string]: number;
            };
            /**
             * Plugin Usage
             * @default {}
             */
            plugin_usage: {
                [key: string]: number;
            };
            /**
             * Retry Rate
             * @default 0
             */
            retry_rate: number;
            /**
             * Webhook Success Rate
             * @default 0
             */
            webhook_success_rate: number;
        };
        /** IntegrationCreate */
        IntegrationCreate: {
            /** Category */
            category: string;
            /**
             * Configuration
             * @default {}
             */
            configuration: {
                [key: string]: unknown;
            };
            /** Name */
            name: string;
            /**
             * Provider
             * @default
             */
            provider: string;
            /**
             * Version
             * @default 1.0.0
             */
            version: string;
        };
        /** IntegrationDashboardOut */
        IntegrationDashboardOut: {
            /**
             * Active Integrations
             * @default 0
             */
            active_integrations: number;
            /**
             * Api Usage Total
             * @default 0
             */
            api_usage_total: number;
            /**
             * Connector Health
             * @default []
             */
            connector_health: components["schemas"]["ConnectorHealthOut"][];
            /**
             * Failed Deliveries
             * @default 0
             */
            failed_deliveries: number;
            /**
             * Plugin Status
             * @default {}
             */
            plugin_status: {
                [key: string]: number;
            };
            /**
             * Webhook Deliveries Total
             * @default 0
             */
            webhook_deliveries_total: number;
        };
        /** IntegrationEventOut */
        IntegrationEventOut: {
            /** Category */
            category: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Event Type */
            event_type: string;
            /** Id */
            id: number;
            /**
             * Payload
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
        };
        /** IntegrationOut */
        IntegrationOut: {
            /** Category */
            category: string;
            /**
             * Configuration
             * @default {}
             */
            configuration: {
                [key: string]: unknown;
            };
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Health Status
             * @default unknown
             */
            health_status: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Provider
             * @default
             */
            provider: string;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1.0.0
             */
            version: string;
        };
        /** IntegrationPatch */
        IntegrationPatch: {
            /** Configuration */
            configuration?: {
                [key: string]: unknown;
            } | null;
            /** Health Status */
            health_status?: string | null;
            /** Status */
            status?: string | null;
            /** Version */
            version?: string | null;
        };
        /** IntegrationStatusOut */
        IntegrationStatusOut: {
            /** Configured */
            configured: boolean;
            /** Name */
            name: string;
        };
        /** InteractionIn */
        InteractionIn: {
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Context
             * @default {}
             */
            context: {
                [key: string]: unknown;
            };
            /** Entity Id */
            entity_id: string;
            /**
             * Entity Type
             * @default opportunity
             */
            entity_type: string;
            /** Interaction Type */
            interaction_type: string;
            /** Sample Weight */
            sample_weight?: number | null;
        };
        /** InteractionOut */
        InteractionOut: {
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /** Id */
            id: number;
            /** Interaction Type */
            interaction_type: string;
            /**
             * Sample Weight
             * @default 1
             */
            sample_weight: number;
            /**
             * User Email
             * @default
             */
            user_email: string;
        };
        /** JobOut */
        JobOut: {
            /**
             * Ats Provider
             * @default
             */
            ats_provider: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Country
             * @default
             */
            country: string;
            /**
             * Employment Type
             * @default
             */
            employment_type: string;
            /**
             * Engineering Relevance Score
             * @default 0
             */
            engineering_relevance_score: number;
            /**
             * Geo Region
             * @default
             */
            geo_region: string;
            /**
             * Job Category
             * @default
             */
            job_category: string;
            /** Job Id */
            job_id: string;
            /**
             * Job Title
             * @default
             */
            job_title: string;
            /**
             * Job Url
             * @default
             */
            job_url: string;
            /**
             * Location
             * @default
             */
            location: string;
            /**
             * Posted Date
             * @default
             */
            posted_date: string;
            /**
             * Seniority
             * @default
             */
            seniority: string;
            /**
             * Technologies
             * @default
             */
            technologies: string;
        };
        /** KanbanColumnOut */
        KanbanColumnOut: {
            /**
             * Deal Count
             * @default 0
             */
            deal_count: number;
            /**
             * Deals
             * @default []
             */
            deals: components["schemas"]["DealOut"][];
            /** Stage Id */
            stage_id: number;
            /** Stage Name */
            stage_name: string;
            /** Stage Order */
            stage_order: number;
            /**
             * Stage Type
             * @default open
             */
            stage_type: string;
            /**
             * Total Value
             * @default 0
             */
            total_value: number;
        };
        /** KanbanOut */
        KanbanOut: {
            /**
             * Columns
             * @default []
             */
            columns: components["schemas"]["KanbanColumnOut"][];
            /** Pipeline Id */
            pipeline_id: number;
            /**
             * Pipeline Name
             * @default
             */
            pipeline_name: string;
            /**
             * Total Deals
             * @default 0
             */
            total_deals: number;
            /**
             * Total Value
             * @default 0
             */
            total_value: number;
        };
        /** KbArticleCreate */
        KbArticleCreate: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Category Id */
            category_id?: number | null;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
        };
        /** KbArticleOut */
        KbArticleOut: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Category Id */
            category_id?: number | null;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /** Id */
            id: number;
            /** Owner Id */
            owner_id?: number | null;
            /** Published At */
            published_at?: string | null;
            /** Status */
            status: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1
             */
            version: number;
            /**
             * View Count
             * @default 0
             */
            view_count: number;
        };
        /** KbArticlePatch */
        KbArticlePatch: {
            /** Body */
            body?: string | null;
            /** Category Id */
            category_id?: number | null;
            /** Status */
            status?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Title */
            title?: string | null;
        };
        /** KbArticleVersionOut */
        KbArticleVersionOut: {
            /** Article Id */
            article_id: number;
            /**
             * Body
             * @default
             */
            body: string;
            /** Created At */
            created_at?: string | null;
            /** Edited By */
            edited_by?: number | null;
            /** Id */
            id: number;
            /**
             * Title
             * @default
             */
            title: string;
            /** Version */
            version: number;
        };
        /** KbAttachmentCreate */
        KbAttachmentCreate: {
            /**
             * Content Type
             * @default
             */
            content_type: string;
            /** Filename */
            filename: string;
            /**
             * Size Bytes
             * @default 0
             */
            size_bytes: number;
        };
        /** KbAttachmentOut */
        KbAttachmentOut: {
            /** Article Id */
            article_id: number;
            /**
             * Content Type
             * @default
             */
            content_type: string;
            /** Created At */
            created_at?: string | null;
            /** Filename */
            filename: string;
            /** Id */
            id: number;
            /**
             * Size Bytes
             * @default 0
             */
            size_bytes: number;
            /** Uploaded By */
            uploaded_by?: number | null;
        };
        /** KbCategoryCreate */
        KbCategoryCreate: {
            /**
             * Description
             * @default
             */
            description: string;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id?: number | null;
        };
        /** KbCategoryOut */
        KbCategoryOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id?: number | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /** KbCategoryPatch */
        KbCategoryPatch: {
            /** Description */
            description?: string | null;
            /** Name */
            name?: string | null;
            /** Parent Id */
            parent_id?: number | null;
        };
        /** KnowledgeSummaryOut */
        KnowledgeSummaryOut: {
            /** Article Id */
            article_id: number;
            /** Summary */
            summary: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
            /**
             * View Count
             * @default 0
             */
            view_count: number;
        };
        /** KpiCreate */
        KpiCreate: {
            /** Category */
            category: string;
            /** Name */
            name: string;
            /** Target Value */
            target_value?: number | null;
            /**
             * Unit
             * @default
             */
            unit: string;
        };
        /** KpiOut */
        KpiOut: {
            /** Category */
            category: string;
            /** Created At */
            created_at?: string | null;
            /** Current Value */
            current_value?: number | null;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Status
             * @default no_target
             */
            status: string;
            /** Target Value */
            target_value?: number | null;
            /**
             * Unit
             * @default
             */
            unit: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** KpiPatch */
        KpiPatch: {
            /** Target Value */
            target_value?: number | null;
            /** Unit */
            unit?: string | null;
        };
        /** KpiValueIn */
        KpiValueIn: {
            /** Value */
            value: number;
        };
        /** KpiValueOut */
        KpiValueOut: {
            /** Id */
            id: number;
            /** Kpi Id */
            kpi_id: number;
            /** Recorded At */
            recorded_at?: string | null;
            /** Value */
            value: number;
        };
        /** LeadOut */
        LeadOut: {
            /**
             * Adjusted Grade
             * @default
             */
            adjusted_grade: string;
            /** Adjusted Score */
            adjusted_score?: number | null;
            /** Combined Priority */
            combined_priority?: number | null;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Company Tier
             * @default
             */
            company_tier: string;
            /**
             * Compliance Flag
             * @default
             */
            compliance_flag: string;
            /**
             * Confidence
             * @default low
             */
            confidence: string;
            /**
             * Coverage
             * @default 0
             */
            coverage: number;
            /**
             * Demand Subscore
             * @default 0
             */
            demand_subscore: number;
            /**
             * Dm Subscore
             * @default 0
             */
            dm_subscore: number;
            /** Grade */
            grade: string;
            /** Human Status */
            human_status?: string | null;
            /** Lead Score */
            lead_score: number;
            /**
             * Opportunity Subscore
             * @default 0
             */
            opportunity_subscore: number;
            /** Priority Rank */
            priority_rank: number;
            /**
             * Prospect Type
             * @default
             */
            prospect_type: string;
            /**
             * Readiness Subscore
             * @default 0
             */
            readiness_subscore: number;
        };
        /**
         * LeadReviewEventOut
         * @description One entry in the review feedback / audit trail (who, when, status change,
         *     notes, and the model grade/score snapshot at the time).
         */
        LeadReviewEventOut: {
            /**
             * Actor Email
             * @default
             */
            actor_email: string;
            /** Actor User Id */
            actor_user_id?: number | null;
            /**
             * Adjusted Grade
             * @default
             */
            adjusted_grade: string;
            /**
             * Adjusted Score
             * @default 0
             */
            adjusted_score: number;
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /**
             * From Status
             * @default
             */
            from_status: string;
            /** Id */
            id: number;
            /**
             * Model Grade
             * @default
             */
            model_grade: string;
            /**
             * Model Score
             * @default 0
             */
            model_score: number;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * To Status
             * @default
             */
            to_status: string;
        };
        /**
         * LeadReviewIn
         * @description A human assessment submission — the status verdict + a reason (required for
         *     score-affecting statuses when the feature is enabled) + an optional expiry.
         */
        LeadReviewIn: {
            /** Expires At */
            expires_at?: string | null;
            /**
             * Human Notes
             * @default
             */
            human_notes: string;
            /** Review Status */
            review_status: string;
        };
        /**
         * LeadReviewOut
         * @description The current human assessment of a lead (separate from the model score).
         */
        LeadReviewOut: {
            /** Company Domain */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /**
             * Human Notes
             * @default
             */
            human_notes: string;
            /** Review Status */
            review_status: string;
            /** Reviewed At */
            reviewed_at?: string | null;
            /** Reviewed By */
            reviewed_by?: number | null;
            /**
             * Reviewed By Email
             * @default
             */
            reviewed_by_email: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** LeadScoreOut */
        LeadScoreOut: {
            /**
             * Adjusted Grade
             * @default
             */
            adjusted_grade: string;
            /** Adjusted Score */
            adjusted_score?: number | null;
            /** Company Domain */
            company_domain: string;
            /**
             * Confidence
             * @default low
             */
            confidence: string;
            /**
             * Coverage
             * @default 0
             */
            coverage: number;
            /** Demand Subscore */
            demand_subscore: number;
            /** Dm Subscore */
            dm_subscore: number;
            /** Grade */
            grade: string;
            /** Lead Score */
            lead_score: number;
            /** Model Version */
            model_version: string;
            /** Opportunity Subscore */
            opportunity_subscore: number;
            /** Priority Rank */
            priority_rank: number;
            /** Prospect Mult */
            prospect_mult: number;
            /**
             * Rationale
             * @default {}
             */
            rationale: {
                [key: string]: unknown;
            };
            /** Readiness Subscore */
            readiness_subscore: number;
            /** Region Mult */
            region_mult: number;
            /** Scored At */
            scored_at?: string | null;
            /** Tier Mult */
            tier_mult: number;
        };
        /**
         * LeadershipSignalOut
         * @description A person-level director+ leadership-movement signal (P-task 8).
         *
         *     Distinct from ``OpportunityOut``: this is who moved (a person), not that an
         *     event happened (a company opportunity). ``company_domain`` may be null when a
         *     historical employer didn't resolve to a catalogued company.
         */
        LeadershipSignalOut: {
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Confidence
             * @default low
             */
            confidence: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Effective Date
             * @default
             */
            effective_date: string;
            /**
             * Event Age Days
             * @default -1
             */
            event_age_days: number;
            /**
             * From Title
             * @default
             */
            from_title: string;
            /**
             * Linkedin Url
             * @default
             */
            linkedin_url: string;
            /**
             * Movement Type
             * @default
             */
            movement_type: string;
            /**
             * Person Name
             * @default
             */
            person_name: string;
            /**
             * Role Function
             * @default
             */
            role_function: string;
            /**
             * Seniority Band
             * @default
             */
            seniority_band: string;
            /** Signal Id */
            signal_id: string;
            /**
             * Source
             * @default
             */
            source: string;
            /**
             * Summary
             * @default
             */
            summary: string;
            /**
             * To Title
             * @default
             */
            to_title: string;
        };
        /** MergeBody */
        MergeBody: {
            /** Target Domain */
            target_domain: string;
        };
        /** MessageForwardIn */
        MessageForwardIn: {
            /**
             * Body
             * @default
             */
            body: string;
            /**
             * Body Html
             * @default
             */
            body_html: string;
            /**
             * Subject
             * @default
             */
            subject: string;
            /** To Email */
            to_email: string;
        };
        /** MessagePreviewOut */
        MessagePreviewOut: {
            /**
             * Attachments
             * @default []
             */
            attachments: components["schemas"]["EmailAttachmentOut"][];
            /**
             * Body Html Safe
             * @default
             */
            body_html_safe: string;
            /**
             * Body Plain
             * @default
             */
            body_plain: string;
            /** Conversation Id */
            conversation_id?: number | null;
            /**
             * Folder
             * @default inbox
             */
            folder: string;
            /** Id */
            id: number;
            /**
             * Is Important
             * @default false
             */
            is_important: boolean;
            /**
             * Is Read
             * @default false
             */
            is_read: boolean;
            /**
             * Is Starred
             * @default false
             */
            is_starred: boolean;
            /**
             * Subject
             * @default
             */
            subject: string;
        };
        /** MessageReplyIn */
        MessageReplyIn: {
            /** Body */
            body: string;
            /**
             * Body Html
             * @default
             */
            body_html: string;
            /**
             * Subject
             * @default
             */
            subject: string;
            /**
             * To Email
             * @default
             */
            to_email: string;
        };
        /** MessageScheduleIn */
        MessageScheduleIn: {
            /** Cancel At */
            cancel_at?: string | null;
            /**
             * Scheduled At
             * Format: date-time
             */
            scheduled_at: string;
        };
        /** MicrosoftAuthBody */
        MicrosoftAuthBody: {
            /** Id Token */
            id_token: string;
        };
        /** MlModelDetailOut */
        MlModelDetailOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Feature Importance
             * @default {}
             */
            feature_importance: {
                [key: string]: unknown;
            };
            /**
             * Feature Version
             * @default
             */
            feature_version: string;
            /** Id */
            id: number;
            /**
             * Metrics
             * @default {}
             */
            metrics: {
                [key: string]: unknown;
            };
            /**
             * Model Metadata
             * @default {}
             */
            model_metadata: {
                [key: string]: unknown;
            };
            /**
             * Model Type
             * @default
             */
            model_type: string;
            /** Name */
            name: string;
            /** Promoted At */
            promoted_at?: string | null;
            /** Status */
            status: string;
            /** Version */
            version: string;
        };
        /** MlModelOut */
        MlModelOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Feature Version
             * @default
             */
            feature_version: string;
            /** Id */
            id: number;
            /**
             * Metrics
             * @default {}
             */
            metrics: {
                [key: string]: unknown;
            };
            /**
             * Model Type
             * @default
             */
            model_type: string;
            /** Name */
            name: string;
            /** Status */
            status: string;
            /** Version */
            version: string;
        };
        /** MlStatusOut */
        MlStatusOut: {
            /** Decay Half Lives */
            decay_half_lives: {
                [key: string]: unknown;
            };
            /** Embedding Backend */
            embedding_backend: string;
            /** Embedding Count */
            embedding_count: number;
            /** Embedding Dim */
            embedding_dim: number;
            /** Embedding Model */
            embedding_model: string;
            /** Feature Row Count */
            feature_row_count: number;
            /** Feature Version */
            feature_version: string;
            /** Interaction Count */
            interaction_count: number;
            /** Ml Enabled */
            ml_enabled: boolean;
            /** Model Count */
            model_count: number;
            /** Production Model */
            production_model?: string | null;
            /**
             * Recommendation Count
             * @default 0
             */
            recommendation_count: number;
            /** Training Run Count */
            training_run_count: number;
        };
        /** NewsSeedResult */
        NewsSeedResult: {
            /** Created */
            created: number;
            /** Total */
            total: number;
            /** Updated */
            updated: number;
        };
        /** NewsSourceIn */
        NewsSourceIn: {
            /**
             * Adapter Type
             * @default rss
             */
            adapter_type: string;
            /**
             * Credibility
             * @default 50
             */
            credibility: number;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Name */
            name: string;
            /**
             * Publisher
             * @default
             */
            publisher: string;
            /**
             * Url
             * @default
             */
            url: string;
        };
        /** NewsSourceOut */
        NewsSourceOut: {
            /**
             * Adapter Type
             * @default
             */
            adapter_type: string;
            /**
             * Credibility
             * @default 50
             */
            credibility: number;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Id */
            id: number;
            /** Last Collected At */
            last_collected_at?: string | null;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Publisher
             * @default
             */
            publisher: string;
            /**
             * Url
             * @default
             */
            url: string;
        };
        /** NewsSourcePatch */
        NewsSourcePatch: {
            /** Adapter Type */
            adapter_type?: string | null;
            /** Credibility */
            credibility?: number | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Name */
            name?: string | null;
            /** Publisher */
            publisher?: string | null;
            /** Url */
            url?: string | null;
        };
        /** NextActionOut */
        NextActionOut: {
            /**
             * Action
             * @default
             */
            action: string;
            /**
             * Priority
             * @default
             */
            priority: string;
            /**
             * Reason
             * @default
             */
            reason: string;
        };
        /** NextBestContactOut */
        NextBestContactOut: {
            contact: components["schemas"]["ContactRefOut"];
            follow_up?: components["schemas"]["FollowUpOut"] | null;
            next_action?: components["schemas"]["NextActionOut"] | null;
            /**
             * Priority
             * @default
             */
            priority: string;
            /**
             * Reasons
             * @default []
             */
            reasons: string[];
            /** Relationship Score */
            relationship_score?: number | null;
            /**
             * Relationship Status
             * @default
             */
            relationship_status: string;
            /**
             * Risk Flags
             * @default []
             */
            risk_flags: string[];
            /**
             * Risk Severity
             * @default
             */
            risk_severity: string;
            /**
             * Score
             * @default 0
             */
            score: number;
        };
        /** NotificationOut */
        NotificationOut: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Created At */
            created_at?: string | null;
            /** Entity Id */
            entity_id?: string | null;
            /** Entity Type */
            entity_type?: string | null;
            /** Id */
            id: number;
            /**
             * Is Read
             * @default false
             */
            is_read: boolean;
            /** Notif Type */
            notif_type: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** User Id */
            user_id: number;
        };
        /** OAuthCredentialCreate */
        OAuthCredentialCreate: {
            /**
             * Client Id
             * @default
             */
            client_id: string;
            /** Client Secret */
            client_secret?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Name */
            name: string;
            /** Provider */
            provider: string;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
        };
        /** OAuthCredentialCreatedOut */
        OAuthCredentialCreatedOut: {
            /**
             * Client Id
             * @default
             */
            client_id: string;
            /** Client Secret */
            client_secret: string;
            /** Created At */
            created_at?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Id */
            id: number;
            /** Last Used At */
            last_used_at?: string | null;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Provider */
            provider: string;
            /**
             * Request Count
             * @default 0
             */
            request_count: number;
            /** Revoked At */
            revoked_at?: string | null;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
            /** Status */
            status: string;
        };
        /** OAuthCredentialOut */
        OAuthCredentialOut: {
            /**
             * Client Id
             * @default
             */
            client_id: string;
            /** Created At */
            created_at?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Id */
            id: number;
            /** Last Used At */
            last_used_at?: string | null;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Provider */
            provider: string;
            /**
             * Request Count
             * @default 0
             */
            request_count: number;
            /** Revoked At */
            revoked_at?: string | null;
            /**
             * Scopes
             * @default []
             */
            scopes: string[];
            /** Status */
            status: string;
        };
        /** OppAlignmentOut */
        OppAlignmentOut: {
            /**
             * Best Department
             * @default
             */
            best_department: string;
            contact?: components["schemas"]["ContactRefOut"] | null;
            /**
             * Label
             * @default
             */
            label: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Opportunity Type
             * @default
             */
            opportunity_type: string;
            /**
             * Reason
             * @default
             */
            reason: string;
        };
        /** OppIntelOut */
        OppIntelOut: {
            /**
             * Backups
             * @default []
             */
            backups: components["schemas"]["ContactRefOut"][];
            best?: components["schemas"]["ContactRefOut"] | null;
            /**
             * Best Department
             * @default
             */
            best_department: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Opportunity Type
             * @default
             */
            opportunity_type: string;
            /**
             * Reason
             * @default
             */
            reason: string;
            /**
             * Relationship Status
             * @default
             */
            relationship_status: string;
            suggested_action?: components["schemas"]["NextActionOut"] | null;
        };
        /**
         * OpportunityDetailOut
         * @description Full opportunity intelligence for the expandable detail panel.
         */
        OpportunityDetailOut: {
            /**
             * Ai Reasoning
             * @default
             */
            ai_reasoning: string;
            /**
             * Ai Summary
             * @default
             */
            ai_summary: string;
            /**
             * Article Title
             * @default
             */
            article_title: string;
            /**
             * Article Url
             * @default
             */
            article_url: string;
            /**
             * Business Impact
             * @default
             */
            business_impact: string;
            /**
             * Canonical Url
             * @default
             */
            canonical_url: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Company News Signal
             * @default
             */
            company_news_signal: string;
            /**
             * Confidence Breakdown
             * @default {}
             */
            confidence_breakdown: {
                [key: string]: unknown;
            };
            /**
             * Confidence Score
             * @default 0
             */
            confidence_score: number;
            /**
             * Countries
             * @default []
             */
            countries: string[];
            /**
             * Effective Opportunity Score
             * @default 0
             */
            effective_opportunity_score: number;
            /**
             * Entity Fingerprint
             * @default
             */
            entity_fingerprint: string;
            /**
             * Event Age Days
             * @default -1
             */
            event_age_days: number;
            /**
             * Executive Summary
             * @default
             */
            executive_summary: string;
            /** Ingested At */
            ingested_at?: string | null;
            /**
             * Is Relevant
             * @default true
             */
            is_relevant: boolean;
            /**
             * Keywords
             * @default []
             */
            keywords: string[];
            /**
             * Lead Readiness Score
             * @default 0
             */
            lead_readiness_score: number;
            /**
             * Lifecycle Status
             * @default NEW
             */
            lifecycle_status: string;
            /**
             * Merged Into
             * @default
             */
            merged_into: string;
            /**
             * Normalized Title
             * @default
             */
            normalized_title: string;
            /**
             * Opportunity Category
             * @default
             */
            opportunity_category: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Opportunity Score
             * @default 0
             */
            opportunity_score: number;
            /**
             * Opportunity Subtype
             * @default
             */
            opportunity_subtype: string;
            /**
             * Opportunity Type
             * @default
             */
            opportunity_type: string;
            /**
             * Organizations
             * @default []
             */
            organizations: string[];
            /**
             * People
             * @default []
             */
            people: string[];
            /**
             * Products
             * @default []
             */
            products: string[];
            /**
             * Published Date
             * @default
             */
            published_date: string;
            /**
             * Related
             * @default []
             */
            related: components["schemas"]["OpportunityOut"][];
            /**
             * Related Group Id
             * @default
             */
            related_group_id: string;
            /**
             * Reviews
             * @default []
             */
            reviews: components["schemas"]["OpportunityReviewOut"][];
            /**
             * Source
             * @default
             */
            source: string;
            /**
             * Source Credibility
             * @default 0
             */
            source_credibility: number;
            /**
             * Source Type
             * @default
             */
            source_type: string;
            /**
             * Sources
             * @default []
             */
            sources: components["schemas"]["OpportunitySourceOut"][];
            /**
             * Summary
             * @default
             */
            summary: string;
            /**
             * Technologies
             * @default []
             */
            technologies: string[];
            /**
             * Technology Focus
             * @default
             */
            technology_focus: string;
            /**
             * Timeline
             * @default []
             */
            timeline: components["schemas"]["OpportunityTimelineItemOut"][];
            /**
             * Validation Status
             * @default
             */
            validation_status: string;
            /**
             * Why This Matters
             * @default
             */
            why_this_matters: string;
        };
        /** OpportunityOut */
        OpportunityOut: {
            /**
             * Ai Summary
             * @default
             */
            ai_summary: string;
            /**
             * Article Title
             * @default
             */
            article_title: string;
            /**
             * Article Url
             * @default
             */
            article_url: string;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Company News Signal
             * @default
             */
            company_news_signal: string;
            /**
             * Confidence Score
             * @default 0
             */
            confidence_score: number;
            /**
             * Effective Opportunity Score
             * @default 0
             */
            effective_opportunity_score: number;
            /**
             * Event Age Days
             * @default -1
             */
            event_age_days: number;
            /**
             * Executive Summary
             * @default
             */
            executive_summary: string;
            /**
             * Is Relevant
             * @default true
             */
            is_relevant: boolean;
            /**
             * Lead Readiness Score
             * @default 0
             */
            lead_readiness_score: number;
            /**
             * Lifecycle Status
             * @default NEW
             */
            lifecycle_status: string;
            /**
             * Opportunity Category
             * @default
             */
            opportunity_category: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Opportunity Score
             * @default 0
             */
            opportunity_score: number;
            /**
             * Opportunity Subtype
             * @default
             */
            opportunity_subtype: string;
            /**
             * Opportunity Type
             * @default
             */
            opportunity_type: string;
            /**
             * Published Date
             * @default
             */
            published_date: string;
            /**
             * Related Group Id
             * @default
             */
            related_group_id: string;
            /**
             * Source
             * @default
             */
            source: string;
            /**
             * Source Credibility
             * @default 0
             */
            source_credibility: number;
            /**
             * Source Type
             * @default
             */
            source_type: string;
            /**
             * Summary
             * @default
             */
            summary: string;
            /**
             * Technologies
             * @default []
             */
            technologies: string[];
            /**
             * Technology Focus
             * @default
             */
            technology_focus: string;
            /**
             * Validation Status
             * @default
             */
            validation_status: string;
        };
        /**
         * OpportunityReviewIn
         * @description A manual-review action. ``target_opportunity_id`` is required for merge;
         *     ``new_type`` for change_type; ``detail`` optional context / internal note.
         */
        OpportunityReviewIn: {
            /** Action */
            action: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** New Type */
            new_type?: string | null;
            /** Target Opportunity Id */
            target_opportunity_id?: string | null;
        };
        /** OpportunityReviewOut */
        OpportunityReviewOut: {
            /** Action */
            action: string;
            /**
             * Actor Email
             * @default
             */
            actor_email: string;
            /**
             * After Snapshot
             * @default {}
             */
            after_snapshot: {
                [key: string]: unknown;
            };
            /**
             * Before Snapshot
             * @default {}
             */
            before_snapshot: {
                [key: string]: unknown;
            };
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Id */
            id: number;
        };
        /** OpportunitySourceOut */
        OpportunitySourceOut: {
            /**
             * Canonical Url
             * @default
             */
            canonical_url: string;
            /** Collected At */
            collected_at?: string | null;
            /**
             * Credibility
             * @default 0
             */
            credibility: number;
            /** Id */
            id: number;
            /**
             * Published At
             * @default
             */
            published_at: string;
            /**
             * Publisher
             * @default
             */
            publisher: string;
            /**
             * Source Name
             * @default
             */
            source_name: string;
            /**
             * Source Type
             * @default
             */
            source_type: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Url
             * @default
             */
            url: string;
        };
        /** OpportunityTimelineItemOut */
        OpportunityTimelineItemOut: {
            /**
             * Article Title
             * @default
             */
            article_title: string;
            /**
             * Effective Opportunity Score
             * @default 0
             */
            effective_opportunity_score: number;
            /**
             * Is Current
             * @default false
             */
            is_current: boolean;
            /**
             * Lifecycle Status
             * @default NEW
             */
            lifecycle_status: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Opportunity Subtype
             * @default
             */
            opportunity_subtype: string;
            /**
             * Opportunity Type
             * @default
             */
            opportunity_type: string;
            /**
             * Published Date
             * @default
             */
            published_date: string;
        };
        /** OrgUnitCreate */
        OrgUnitCreate: {
            /** Lead User Id */
            lead_user_id?: number | null;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id?: number | null;
            /** Unit Type */
            unit_type: string;
        };
        /** OrgUnitMemberIn */
        OrgUnitMemberIn: {
            /**
             * Role
             * @default member
             */
            role: string;
            /** User Id */
            user_id: number;
        };
        /** OrgUnitMemberOut */
        OrgUnitMemberOut: {
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /** Role */
            role: string;
            /** Unit Id */
            unit_id: number;
            /**
             * User Email
             * @default
             */
            user_email: string;
            /** User Id */
            user_id: number;
        };
        /** OrgUnitOut */
        OrgUnitOut: {
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /** Lead User Id */
            lead_user_id?: number | null;
            /**
             * Member Count
             * @default 0
             */
            member_count: number;
            /** Name */
            name: string;
            /** Organization Id */
            organization_id: number;
            /** Parent Id */
            parent_id?: number | null;
            /** Unit Type */
            unit_type: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** OrgUnitPatch */
        OrgUnitPatch: {
            /** Lead User Id */
            lead_user_id?: number | null;
            /** Name */
            name?: string | null;
            /** Parent Id */
            parent_id?: number | null;
        };
        /** OrganizationCreate */
        OrganizationCreate: {
            /**
             * Feature Flags
             * @default {}
             */
            feature_flags: {
                [key: string]: unknown;
            };
            /**
             * Industry
             * @default
             */
            industry: string;
            /** Name */
            name: string;
            /**
             * Settings
             * @default {}
             */
            settings: {
                [key: string]: unknown;
            };
            /**
             * Size
             * @default
             */
            size: string;
            /** Slug */
            slug: string;
        };
        /** OrganizationOut */
        OrganizationOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Feature Flags
             * @default {}
             */
            feature_flags: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /**
             * Industry
             * @default
             */
            industry: string;
            /** Name */
            name: string;
            /**
             * Settings
             * @default {}
             */
            settings: {
                [key: string]: unknown;
            };
            /**
             * Size
             * @default
             */
            size: string;
            /** Slug */
            slug: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** OrganizationPatch */
        OrganizationPatch: {
            /** Feature Flags */
            feature_flags?: {
                [key: string]: unknown;
            } | null;
            /** Industry */
            industry?: string | null;
            /** Name */
            name?: string | null;
            /** Settings */
            settings?: {
                [key: string]: unknown;
            } | null;
            /** Size */
            size?: string | null;
        };
        /** OutreachActivityOut */
        OutreachActivityOut: {
            /**
             * Actor Email
             * @default
             */
            actor_email: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Id */
            id: number;
            /** Outreach Lead Id */
            outreach_lead_id: number;
            /** Type */
            type: string;
        };
        /** OutreachAnalytics */
        OutreachAnalytics: {
            /**
             * Drafts
             * @default 0
             */
            drafts: number;
            /**
             * Funnel
             * @default []
             */
            funnel: components["schemas"]["OutreachStageCount"][];
            /**
             * Lost
             * @default 0
             */
            lost: number;
            /**
             * Open Leads
             * @default 0
             */
            open_leads: number;
            /**
             * Pending Approval
             * @default 0
             */
            pending_approval: number;
            /**
             * Replied
             * @default 0
             */
            replied: number;
            /**
             * Reply Rate
             * @default 0
             */
            reply_rate: number;
            /**
             * Sent
             * @default 0
             */
            sent: number;
            /**
             * Total Leads
             * @default 0
             */
            total_leads: number;
            /**
             * Win Rate
             * @default 0
             */
            win_rate: number;
            /**
             * Won
             * @default 0
             */
            won: number;
        };
        /** OutreachAnalyticsDetailOut */
        OutreachAnalyticsDetailOut: {
            /**
             * Conversion Rate
             * @default 0
             */
            conversion_rate: number;
            /**
             * Emails Sent
             * @default 0
             */
            emails_sent: number;
            /**
             * Meeting Rate
             * @default 0
             */
            meeting_rate: number;
            /**
             * Meetings
             * @default 0
             */
            meetings: number;
            /**
             * Replies
             * @default 0
             */
            replies: number;
            /**
             * Reply Rate
             * @default 0
             */
            reply_rate: number;
        };
        /**
         * OutreachContactOut
         * @description A decision maker presented as an outreach contact (reused, not duplicated).
         */
        OutreachContactOut: {
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /** Confidence Score */
            confidence_score?: number | null;
            /** Decision Maker Id */
            decision_maker_id: number;
            /**
             * Department
             * @default
             */
            department: string;
            /**
             * Email
             * @default
             */
            email: string;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /** Influence Score */
            influence_score?: number | null;
            /**
             * Is Primary
             * @default false
             */
            is_primary: boolean;
            /**
             * Linkedin Url
             * @default
             */
            linkedin_url: string;
            /**
             * Next Action
             * @default
             */
            next_action: string;
            /**
             * Next Action Reason
             * @default
             */
            next_action_reason: string;
            /**
             * Recommendation Rank
             * @default
             */
            recommendation_rank: string;
            /**
             * Recommendation Reason
             * @default []
             */
            recommendation_reason: string[];
            /**
             * Relationship Status
             * @default
             */
            relationship_status: string;
            /**
             * Seniority
             * @default
             */
            seniority: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** OutreachDashboardOut */
        OutreachDashboardOut: {
            /**
             * Open Tasks
             * @default 0
             */
            open_tasks: number;
            /**
             * Overdue Follow Ups
             * @default 0
             */
            overdue_follow_ups: number;
            /**
             * Overdue Tasks
             * @default []
             */
            overdue_tasks: components["schemas"]["OutreachTaskOut"][];
            /**
             * Recent Activity
             * @default []
             */
            recent_activity: components["schemas"]["OutreachActivityOut"][];
            /**
             * Tasks Due Today
             * @default []
             */
            tasks_due_today: components["schemas"]["OutreachTaskOut"][];
            /**
             * Total Meetings This Week
             * @default 0
             */
            total_meetings_this_week: number;
            /**
             * Upcoming Follow Ups
             * @default []
             */
            upcoming_follow_ups: components["schemas"]["OutreachFollowUpItem"][];
            /**
             * Upcoming Meetings
             * @default []
             */
            upcoming_meetings: components["schemas"]["OutreachMeetingOut"][];
        };
        /** OutreachFollowUpItem */
        OutreachFollowUpItem: {
            /** Company Domain */
            company_domain: string;
            /** Company Name */
            company_name: string;
            /** Days Since Activity */
            days_since_activity?: number | null;
            /** Days Until */
            days_until: number;
            /**
             * Due At
             * Format: date-time
             */
            due_at: string;
            /** Is Overdue */
            is_overdue: boolean;
            /** Lead Id */
            lead_id: number;
            /**
             * Reminder Priority
             * @default low
             */
            reminder_priority: string;
            /**
             * Stage
             * @default
             */
            stage: string;
        };
        /** OutreachLeadCreate */
        OutreachLeadCreate: {
            /** Company Domain */
            company_domain: string;
            /** Owner Id */
            owner_id?: number | null;
            /** Service Interest */
            service_interest?: ("staffing" | "engineering" | "training") | null;
        };
        /** OutreachLeadDetail */
        OutreachLeadDetail: {
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Contacts
             * @default []
             */
            contacts: components["schemas"]["OutreachContactOut"][];
            /** Created At */
            created_at?: string | null;
            /**
             * Grade
             * @default
             */
            grade: string;
            /** Id */
            id: number;
            /** Last Activity At */
            last_activity_at?: string | null;
            /** Lead Score */
            lead_score?: number | null;
            /** Next Action At */
            next_action_at?: string | null;
            /**
             * Open Messages
             * @default 0
             */
            open_messages: number;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            primary_contact?: components["schemas"]["OutreachContactOut"] | null;
            /**
             * Priority
             * @default
             */
            priority: string;
            /**
             * Qualification Reason
             * @default
             */
            qualification_reason: string;
            /** Qualified At */
            qualified_at?: string | null;
            /**
             * Recommended Offering
             * @default
             */
            recommended_offering: string;
            /**
             * Recommended Pitch
             * @default
             */
            recommended_pitch: string;
            /**
             * Reply Count
             * @default 0
             */
            reply_count: number;
            /**
             * Sent Messages
             * @default 0
             */
            sent_messages: number;
            /** Service Interest */
            service_interest?: string | null;
            /**
             * Signal Summary
             * @default
             */
            signal_summary: string;
            /**
             * Signals
             * @default []
             */
            signals: components["schemas"]["OutreachSignalOut"][];
            /**
             * Source
             * @default discovery
             */
            source: string;
            /** Stage */
            stage: string;
        };
        /**
         * OutreachLeadOut
         * @description A pipeline row: outreach state + live intelligence read from platform tables.
         */
        OutreachLeadOut: {
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Grade
             * @default
             */
            grade: string;
            /** Id */
            id: number;
            /** Last Activity At */
            last_activity_at?: string | null;
            /** Lead Score */
            lead_score?: number | null;
            /** Next Action At */
            next_action_at?: string | null;
            /**
             * Open Messages
             * @default 0
             */
            open_messages: number;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            primary_contact?: components["schemas"]["OutreachContactOut"] | null;
            /**
             * Priority
             * @default
             */
            priority: string;
            /**
             * Qualification Reason
             * @default
             */
            qualification_reason: string;
            /** Qualified At */
            qualified_at?: string | null;
            /**
             * Reply Count
             * @default 0
             */
            reply_count: number;
            /**
             * Sent Messages
             * @default 0
             */
            sent_messages: number;
            /** Service Interest */
            service_interest?: string | null;
            /**
             * Signal Summary
             * @default
             */
            signal_summary: string;
            /**
             * Source
             * @default discovery
             */
            source: string;
            /** Stage */
            stage: string;
        };
        /** OutreachLeadPatch */
        OutreachLeadPatch: {
            /** Next Action At */
            next_action_at?: string | null;
            /** Owner Id */
            owner_id?: number | null;
            /** Primary Dm Id */
            primary_dm_id?: number | null;
            /** Service Interest */
            service_interest?: ("staffing" | "engineering" | "training") | null;
            /** Stage */
            stage?: ("research_complete" | "outreach_ready" | "contacted" | "replied" | "interested" | "meeting_scheduled" | "proposal_sent" | "won" | "lost") | null;
        };
        /** OutreachMeetingIn */
        OutreachMeetingIn: {
            /** Company Domain */
            company_domain?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Duration Minutes
             * @default 30
             */
            duration_minutes: number;
            /**
             * Meeting Type
             * @default call
             */
            meeting_type: string;
            /**
             * Next Action
             * @default
             */
            next_action: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Outcome
             * @default
             */
            outcome: string;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /**
             * Participants
             * @default []
             */
            participants: string[];
            /**
             * Scheduled At
             * Format: date-time
             */
            scheduled_at: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** OutreachMeetingOut */
        OutreachMeetingOut: {
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Created By Email
             * @default
             */
            created_by_email: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Decision Maker Name
             * @default
             */
            decision_maker_name: string;
            /**
             * Duration Minutes
             * @default 30
             */
            duration_minutes: number;
            /** Id */
            id: number;
            /**
             * Is Upcoming
             * @default false
             */
            is_upcoming: boolean;
            /**
             * Meeting Type
             * @default call
             */
            meeting_type: string;
            /**
             * Next Action
             * @default
             */
            next_action: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Outcome
             * @default
             */
            outcome: string;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /**
             * Participants
             * @default []
             */
            participants: unknown[];
            /**
             * Scheduled At
             * Format: date-time
             */
            scheduled_at: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** OutreachMeetingPatch */
        OutreachMeetingPatch: {
            /** Duration Minutes */
            duration_minutes?: number | null;
            /** Meeting Type */
            meeting_type?: string | null;
            /** Next Action */
            next_action?: string | null;
            /** Notes */
            notes?: string | null;
            /** Outcome */
            outcome?: string | null;
            /** Participants */
            participants?: string[] | null;
            /** Scheduled At */
            scheduled_at?: string | null;
            /** Title */
            title?: string | null;
        };
        /** OutreachMessageCreate */
        OutreachMessageCreate: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Subject
             * @default
             */
            subject: string;
            /** Template Id */
            template_id?: number | null;
        };
        /** OutreachMessageOut */
        OutreachMessageOut: {
            /** Approved At */
            approved_at?: string | null;
            /**
             * Approved By Email
             * @default
             */
            approved_by_email: string;
            /**
             * Attachment Count
             * @default 0
             */
            attachment_count: number;
            /**
             * Body
             * @default
             */
            body: string;
            /** Bounced At */
            bounced_at?: string | null;
            /**
             * Can Approve
             * @default false
             */
            can_approve: boolean;
            /** Cancel At */
            cancel_at?: string | null;
            /** Conversation Id */
            conversation_id?: number | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Created By Email
             * @default
             */
            created_by_email: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /** Delivered At */
            delivered_at?: string | null;
            /**
             * Direction
             * @default outbound
             */
            direction: string;
            /**
             * Failed Reason
             * @default
             */
            failed_reason: string;
            /**
             * Folder
             * @default inbox
             */
            folder: string;
            /**
             * From Email
             * @default
             */
            from_email: string;
            /** Id */
            id: number;
            /**
             * Is Archived
             * @default false
             */
            is_archived: boolean;
            /**
             * Is Important
             * @default false
             */
            is_important: boolean;
            /**
             * Is Pinned
             * @default false
             */
            is_pinned: boolean;
            /**
             * Is Read
             * @default false
             */
            is_read: boolean;
            /**
             * Is Starred
             * @default false
             */
            is_starred: boolean;
            /**
             * Is Trashed
             * @default false
             */
            is_trashed: boolean;
            /**
             * Max Retries
             * @default 3
             */
            max_retries: number;
            /** Outreach Lead Id */
            outreach_lead_id: number;
            /** Parent Message Id */
            parent_message_id?: number | null;
            /**
             * Provider
             * @default mock
             */
            provider: string;
            /**
             * Provider Message Id
             * @default
             */
            provider_message_id: string;
            /**
             * Recipient Name
             * @default
             */
            recipient_name: string;
            /**
             * Retry Count
             * @default 0
             */
            retry_count: number;
            /** Scheduled At */
            scheduled_at?: string | null;
            /** Sent At */
            sent_at?: string | null;
            /**
             * Status
             * @default draft
             */
            status: string;
            /**
             * Subject
             * @default
             */
            subject: string;
            /** Template Id */
            template_id?: number | null;
            /**
             * Thread Id
             * @default
             */
            thread_id: string;
            /**
             * To Email
             * @default
             */
            to_email: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** OutreachMessagePatch */
        OutreachMessagePatch: {
            /** Body */
            body?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /** Subject */
            subject?: string | null;
        };
        /** OutreachNoteIn */
        OutreachNoteIn: {
            /** Text */
            text: string;
        };
        /** OutreachPriorityOut */
        OutreachPriorityOut: {
            /**
             * Factors
             * @default []
             */
            factors: string[];
            /**
             * Priority
             * @default
             */
            priority: string;
            /**
             * Score
             * @default 0
             */
            score: number;
        };
        /**
         * OutreachSignalOut
         * @description A one-line intelligence signal surfaced on the lead (from opportunities / demand).
         */
        OutreachSignalOut: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Source Url
             * @default
             */
            source_url: string;
            /**
             * Type
             * @default
             */
            type: string;
        };
        /** OutreachStageCount */
        OutreachStageCount: {
            /** Count */
            count: number;
            /** Stage */
            stage: string;
        };
        /** OutreachSyncResult */
        OutreachSyncResult: {
            /**
             * Created
             * @default 0
             */
            created: number;
            /**
             * Total
             * @default 0
             */
            total: number;
            /**
             * Updated
             * @default 0
             */
            updated: number;
        };
        /** OutreachTaskIn */
        OutreachTaskIn: {
            /** Assigned To */
            assigned_to?: number | null;
            /** Company Domain */
            company_domain?: string | null;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Due At */
            due_at?: string | null;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /**
             * Priority
             * @default medium
             */
            priority: string;
            /** Title */
            title: string;
        };
        /** OutreachTaskOut */
        OutreachTaskOut: {
            /** Assigned To */
            assigned_to?: number | null;
            /**
             * Assigned To Email
             * @default
             */
            assigned_to_email: string;
            /** Company Domain */
            company_domain?: string | null;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Completed At */
            completed_at?: string | null;
            /** Completed By */
            completed_by?: number | null;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Created By Email
             * @default
             */
            created_by_email: string;
            /** Decision Maker Id */
            decision_maker_id?: number | null;
            /**
             * Decision Maker Name
             * @default
             */
            decision_maker_name: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** Due At */
            due_at?: string | null;
            /** Id */
            id: number;
            /**
             * Is Overdue
             * @default false
             */
            is_overdue: boolean;
            /** Outreach Lead Id */
            outreach_lead_id?: number | null;
            /**
             * Priority
             * @default medium
             */
            priority: string;
            /**
             * Status
             * @default pending
             */
            status: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** OutreachTaskPatch */
        OutreachTaskPatch: {
            /** Assigned To */
            assigned_to?: number | null;
            /** Description */
            description?: string | null;
            /** Due At */
            due_at?: string | null;
            /** Priority */
            priority?: string | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /** OutreachTemplateIn */
        OutreachTemplateIn: {
            /**
             * Body
             * @default
             */
            body: string;
            /**
             * Category
             * @default
             */
            category: string;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /** Name */
            name: string;
            /**
             * Subject
             * @default
             */
            subject: string;
        };
        /** OutreachTemplateOut */
        OutreachTemplateOut: {
            /**
             * Body
             * @default
             */
            body: string;
            /**
             * Category
             * @default
             */
            category: string;
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /** Id */
            id: number;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /** Name */
            name: string;
            /**
             * Subject
             * @default
             */
            subject: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Variables
             * @default []
             */
            variables: string[];
        };
        /** OutreachThreadOut */
        OutreachThreadOut: {
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /**
             * Has Reply
             * @default false
             */
            has_reply: boolean;
            /** Last At */
            last_at?: string | null;
            /**
             * Message Count
             * @default 0
             */
            message_count: number;
            /**
             * Messages
             * @default []
             */
            messages: components["schemas"]["OutreachMessageOut"][];
            /** Outreach Lead Id */
            outreach_lead_id: number;
            /**
             * Subject
             * @default
             */
            subject: string;
            /** Thread Id */
            thread_id: string;
        };
        /** Page */
        Page: {
            /** Items */
            items: unknown[];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[CompanySummary] */
        Page_CompanySummary_: {
            /** Items */
            items: components["schemas"]["CompanySummary"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[DecisionMakerOut] */
        Page_DecisionMakerOut_: {
            /** Items */
            items: components["schemas"]["DecisionMakerOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[DemandSignalOut] */
        Page_DemandSignalOut_: {
            /** Items */
            items: components["schemas"]["DemandSignalOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[EmailConversationOut] */
        Page_EmailConversationOut_: {
            /** Items */
            items: components["schemas"]["EmailConversationOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[ExecutionOut] */
        Page_ExecutionOut_: {
            /** Items */
            items: components["schemas"]["ExecutionOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[LeadOut] */
        Page_LeadOut_: {
            /** Items */
            items: components["schemas"]["LeadOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[LeadershipSignalOut] */
        Page_LeadershipSignalOut_: {
            /** Items */
            items: components["schemas"]["LeadershipSignalOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[OpportunityOut] */
        Page_OpportunityOut_: {
            /** Items */
            items: components["schemas"]["OpportunityOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[OutreachLeadOut] */
        Page_OutreachLeadOut_: {
            /** Items */
            items: components["schemas"]["OutreachLeadOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[OutreachMeetingOut] */
        Page_OutreachMeetingOut_: {
            /** Items */
            items: components["schemas"]["OutreachMeetingOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[OutreachMessageOut] */
        Page_OutreachMessageOut_: {
            /** Items */
            items: components["schemas"]["OutreachMessageOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[OutreachTaskOut] */
        Page_OutreachTaskOut_: {
            /** Items */
            items: components["schemas"]["OutreachTaskOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** Page[ReviewItemOut] */
        Page_ReviewItemOut_: {
            /** Items */
            items: components["schemas"]["ReviewItemOut"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Pages */
            pages: number;
            /** Total */
            total: number;
        };
        /** PipelineAgingOut */
        PipelineAgingOut: {
            /** Bucket */
            bucket: string;
            /**
             * Deal Count
             * @default 0
             */
            deal_count: number;
        };
        /** PipelineComponentHealth */
        PipelineComponentHealth: {
            /** Component */
            component: string;
            /**
             * Failed Runs
             * @default 0
             */
            failed_runs: number;
            /**
             * Last Duration Ms
             * @default 0
             */
            last_duration_ms: number;
            /** Last Run */
            last_run?: string | null;
            /** Last Status */
            last_status: string;
            /** Last Success */
            last_success?: string | null;
        };
        /** PipelineCreate */
        PipelineCreate: {
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Is Default
             * @default false
             */
            is_default: boolean;
            /** Name */
            name: string;
            /**
             * Stages
             * @default []
             */
            stages: components["schemas"]["PipelineStageCreate"][];
        };
        /** PipelineOut */
        PipelineOut: {
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /**
             * Is Default
             * @default false
             */
            is_default: boolean;
            /** Name */
            name: string;
            /**
             * Stage Count
             * @default 0
             */
            stage_count: number;
            /**
             * Stages
             * @default []
             */
            stages: components["schemas"]["PipelineStageOut"][];
            /** Updated At */
            updated_at?: string | null;
        };
        /** PipelinePatch */
        PipelinePatch: {
            /** Description */
            description?: string | null;
            /** Is Active */
            is_active?: boolean | null;
            /** Is Default */
            is_default?: boolean | null;
            /** Name */
            name?: string | null;
        };
        /** PipelineRunOut */
        PipelineRunOut: {
            /** Component */
            component: string;
            /** Duration Ms */
            duration_ms: number;
            /** Finished At */
            finished_at?: string | null;
            /** Mode */
            mode: string;
            /** Pipeline Id */
            pipeline_id: string;
            /** Records Created */
            records_created: number;
            /** Records Processed */
            records_processed: number;
            /** Records Review */
            records_review: number;
            /** Records Updated */
            records_updated: number;
            /** Run Id */
            run_id: number;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Trigger */
            trigger: string;
        };
        /** PipelineStageCreate */
        PipelineStageCreate: {
            /** Name */
            name: string;
            /**
             * Probability
             * @default 0
             */
            probability: number;
            /**
             * Stage Order
             * @default 1
             */
            stage_order: number;
            /**
             * Stage Type
             * @default open
             */
            stage_type: string;
        };
        /** PipelineStageOut */
        PipelineStageOut: {
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Pipeline Id */
            pipeline_id: number;
            /**
             * Probability
             * @default 0
             */
            probability: number;
            /**
             * Stage Order
             * @default 1
             */
            stage_order: number;
            /**
             * Stage Type
             * @default open
             */
            stage_type: string;
        };
        /** PipelineStagePatch */
        PipelineStagePatch: {
            /** Name */
            name?: string | null;
            /** Probability */
            probability?: number | null;
            /** Stage Order */
            stage_order?: number | null;
            /** Stage Type */
            stage_type?: string | null;
        };
        /**
         * PipelineStatusOut
         * @description Data-freshness signal. `last_successful_refresh` is when a full pipeline last
         *     completed (scoring is the final stage), so the UI can anchor to the last *good*
         *     refresh and warn when the latest run failed or is mid-flight.
         */
        PipelineStatusOut: {
            /** In Progress */
            in_progress: boolean;
            /** Last Successful Refresh */
            last_successful_refresh?: string | null;
            /** Latest Run Component */
            latest_run_component?: string | null;
            /** Latest Run Status */
            latest_run_status: string;
        };
        /** PluginCreate */
        PluginCreate: {
            /**
             * Execution Hooks
             * @default []
             */
            execution_hooks: string[];
            /** Name */
            name: string;
            /**
             * Permissions
             * @default []
             */
            permissions: string[];
            /**
             * Plugin Metadata
             * @default {}
             */
            plugin_metadata: {
                [key: string]: unknown;
            };
            /**
             * Version
             * @default 1.0.0
             */
            version: string;
        };
        /** PluginExecutionOut */
        PluginExecutionOut: {
            /**
             * Detail
             * @default {}
             */
            detail: {
                [key: string]: unknown;
            };
            /** Executed At */
            executed_at?: string | null;
            /** Hook Name */
            hook_name: string;
            /** Id */
            id: number;
            /** Plugin Id */
            plugin_id: number;
            /** Status */
            status: string;
        };
        /** PluginOut */
        PluginOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Execution Hooks
             * @default []
             */
            execution_hooks: string[];
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Permissions
             * @default []
             */
            permissions: string[];
            /**
             * Plugin Metadata
             * @default {}
             */
            plugin_metadata: {
                [key: string]: unknown;
            };
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1.0.0
             */
            version: string;
        };
        /** PluginPatch */
        PluginPatch: {
            /** Execution Hooks */
            execution_hooks?: string[] | null;
            /** Permissions */
            permissions?: string[] | null;
            /** Plugin Metadata */
            plugin_metadata?: {
                [key: string]: unknown;
            } | null;
            /** Status */
            status?: string | null;
        };
        /** PromotionResultOut */
        PromotionResultOut: {
            /**
             * Checks
             * @default {}
             */
            checks: {
                [key: string]: unknown;
            };
            /**
             * Metrics
             * @default {}
             */
            metrics: {
                [key: string]: unknown;
            };
            /** Previous Version */
            previous_version?: string | null;
            /** Promoted */
            promoted: boolean;
            /** Reason */
            reason: string;
            /** Version */
            version: string;
        };
        /** QueueStatusOut */
        QueueStatusOut: {
            /**
             * Failed
             * @default 0
             */
            failed: number;
            /**
             * Queued
             * @default 0
             */
            queued: number;
            /**
             * Scheduled
             * @default 0
             */
            scheduled: number;
            /**
             * Sending
             * @default 0
             */
            sending: number;
        };
        /**
         * RankedContactOut
         * @description A ranked decision maker with its recommendation role + deterministic reasons.
         */
        RankedContactOut: {
            contact: components["schemas"]["DecisionMakerOut"];
            /**
             * Rank
             * @default
             */
            rank: string;
            /**
             * Ranking Score
             * @default 0
             */
            ranking_score: number;
            /**
             * Reasons
             * @default []
             */
            reasons: string[];
        };
        /** RecommendationOut */
        RecommendationOut: {
            /**
             * Company Domain
             * @default
             */
            company_domain: string;
            /** Created At */
            created_at?: string | null;
            /** Entity Id */
            entity_id: string;
            /**
             * Entity Type
             * @default company
             */
            entity_type: string;
            /**
             * Model Version
             * @default
             */
            model_version: string;
            /**
             * Probability
             * @default 0
             */
            probability: number;
        };
        /** RejectBody */
        RejectBody: {
            /** Reason */
            reason?: string | null;
        };
        /** RelatedArticleOut */
        RelatedArticleOut: {
            /** Article Id */
            article_id: number;
            /**
             * Reason
             * @default
             */
            reason: string;
            /**
             * Score
             * @default 0
             */
            score: number;
            /** Title */
            title: string;
        };
        /** RelationshipGraphOut */
        RelationshipGraphOut: {
            /**
             * Edges
             * @default []
             */
            edges: components["schemas"]["GraphEdgeOut"][];
            /**
             * Nodes
             * @default []
             */
            nodes: components["schemas"]["GraphNodeOut"][];
        };
        /** RenewalScanResultOut */
        RenewalScanResultOut: {
            /**
             * Workflows Fired
             * @default 0
             */
            workflows_fired: number;
        };
        /** ReportScheduleCreate */
        ReportScheduleCreate: {
            /** Frequency */
            frequency: string;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /**
             * Recipient Emails
             * @default []
             */
            recipient_emails: string[];
        };
        /** ReportScheduleOut */
        ReportScheduleOut: {
            /** Created At */
            created_at?: string | null;
            /** Frequency */
            frequency: string;
            /** Id */
            id: number;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Last Run At */
            last_run_at?: string | null;
            /**
             * Recipient Emails
             * @default []
             */
            recipient_emails: string[];
            /** Report Id */
            report_id: number;
        };
        /** ReportSchedulePatch */
        ReportSchedulePatch: {
            /** Frequency */
            frequency?: string | null;
            /** Is Enabled */
            is_enabled?: boolean | null;
            /** Recipient Emails */
            recipient_emails?: string[] | null;
        };
        /** RevenueByDimensionOut */
        RevenueByDimensionOut: {
            /**
             * Deal Count
             * @default 0
             */
            deal_count: number;
            /** Key */
            key: string;
            /**
             * Revenue
             * @default 0
             */
            revenue: number;
        };
        /** RevenueForecastOut */
        RevenueForecastOut: {
            /** Period Type */
            period_type: string;
            /**
             * Periods
             * @default []
             */
            periods: components["schemas"]["ForecastPeriodOut"][];
            /** Pipeline Id */
            pipeline_id?: number | null;
        };
        /** RevenueTargetCreate */
        RevenueTargetCreate: {
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /**
             * Notes
             * @default
             */
            notes: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Period End
             * Format: date-time
             */
            period_end: string;
            /**
             * Period Start
             * Format: date-time
             */
            period_start: string;
            /**
             * Period Type
             * @default monthly
             */
            period_type: string;
            /** Pipeline Id */
            pipeline_id?: number | null;
            /**
             * Scope
             * @default company
             */
            scope: string;
            /**
             * Target Amount
             * @default 0
             */
            target_amount: number;
        };
        /** RevenueTargetOut */
        RevenueTargetOut: {
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Currency
             * @default USD
             */
            currency: string;
            /** Id */
            id: number;
            /**
             * Notes
             * @default
             */
            notes: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Period End
             * Format: date-time
             */
            period_end: string;
            /**
             * Period Start
             * Format: date-time
             */
            period_start: string;
            /** Period Type */
            period_type: string;
            /** Pipeline Id */
            pipeline_id?: number | null;
            /** Scope */
            scope: string;
            /**
             * Target Amount
             * @default 0
             */
            target_amount: number;
            /** Updated At */
            updated_at?: string | null;
        };
        /** ReviewActionOut */
        ReviewActionOut: {
            /** Action */
            action: string;
            /** Actor */
            actor: string;
            /** Created At */
            created_at?: string | null;
            /** Detail */
            detail: string;
            /** From Domain */
            from_domain: string;
            /** Id */
            id: number;
            /** Review Id */
            review_id: number | null;
            /** To Domain */
            to_domain: string;
        };
        /** ReviewActionResult */
        ReviewActionResult: {
            /** Action */
            action: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Id */
            id: number;
            /** Moved */
            moved?: {
                [key: string]: number;
            } | null;
            /** Resolved Domain */
            resolved_domain?: string | null;
            /** Status */
            status: string;
        };
        /**
         * ReviewAdjustmentStats
         * @description Review-adjustment analytics (reconciled Change_05 §7): how human review is
         *     moving grades vs the model. Zeroes when the feature is OFF.
         */
        ReviewAdjustmentStats: {
            /**
             * Active Adjustments
             * @default 0
             */
            active_adjustments: number;
            /**
             * Avg Delta
             * @default 0
             */
            avg_delta: number;
            /**
             * Boosted
             * @default 0
             */
            boosted: number;
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /**
             * Expired
             * @default 0
             */
            expired: number;
            /**
             * Floor Applied
             * @default 0
             */
            floor_applied: number;
            /**
             * Movers
             * @default []
             */
            movers: components["schemas"]["ReviewReportRow"][];
            /**
             * Penalised
             * @default 0
             */
            penalised: number;
            /**
             * Total Delta
             * @default 0
             */
            total_delta: number;
        };
        /** ReviewItemOut */
        ReviewItemOut: {
            /** Confidence */
            confidence: number;
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /** Match Type */
            match_type: string;
            /** Notes */
            notes: string;
            /** Raw Domain */
            raw_domain: string;
            /** Raw Name */
            raw_name: string;
            /** Raw Website */
            raw_website: string;
            /** Resolved Domain */
            resolved_domain: string;
            /** Reviewed At */
            reviewed_at?: string | null;
            /** Source Engine */
            source_engine: string;
            /** Source Record Ref */
            source_record_ref: string;
            /** Status */
            status: string;
            /** Suggested Domain */
            suggested_domain: string;
        };
        /**
         * ReviewReportRow
         * @description A company in one of the review reports, with both verdicts side by side.
         */
        ReviewReportRow: {
            /**
             * Adjusted Grade
             * @default
             */
            adjusted_grade: string;
            /**
             * Adjusted Score
             * @default 0
             */
            adjusted_score: number;
            /** Company Domain */
            company_domain: string;
            /**
             * Company Name
             * @default
             */
            company_name: string;
            /** Disagreement */
            disagreement?: string | null;
            /**
             * Human Notes
             * @default
             */
            human_notes: string;
            /** Human Status */
            human_status?: string | null;
            /**
             * Model Grade
             * @default
             */
            model_grade: string;
            /**
             * Model Score
             * @default 0
             */
            model_score: number;
            /**
             * Override Count
             * @default 0
             */
            override_count: number;
        };
        /**
         * ReviewReports
         * @description The human-review reporting bundle (P-task viii §7 + reconciled Change_05).
         */
        ReviewReports: {
            /**
             * @default {
             *       "active_adjustments": 0,
             *       "avg_delta": 0,
             *       "boosted": 0,
             *       "enabled": false,
             *       "expired": 0,
             *       "floor_applied": 0,
             *       "movers": [],
             *       "penalised": 0,
             *       "total_delta": 0
             *     }
             */
            adjustments: components["schemas"]["ReviewAdjustmentStats"];
            /**
             * Disagreements
             * @default []
             */
            disagreements: components["schemas"]["ReviewReportRow"][];
            /**
             * False Negatives
             * @default []
             */
            false_negatives: components["schemas"]["ReviewReportRow"][];
            /**
             * False Positives
             * @default []
             */
            false_positives: components["schemas"]["ReviewReportRow"][];
            /**
             * Frequently Overridden
             * @default []
             */
            frequently_overridden: components["schemas"]["ReviewReportRow"][];
            /**
             * Status Distribution
             * @default {}
             */
            status_distribution: {
                [key: string]: number;
            };
            /**
             * Strategic Accounts
             * @default []
             */
            strategic_accounts: components["schemas"]["ReviewReportRow"][];
        };
        /** ReviewStatusOut */
        ReviewStatusOut: {
            /** Is Stub */
            is_stub: boolean;
            /**
             * Match Types
             * @default []
             */
            match_types: string[];
            /**
             * Pending Review Items
             * @default 0
             */
            pending_review_items: number;
            /** Validation Status */
            validation_status: string;
        };
        /** RevopsPipelineAnalyticsOut */
        RevopsPipelineAnalyticsOut: {
            /**
             * Aging
             * @default []
             */
            aging: components["schemas"]["PipelineAgingOut"][];
            /**
             * Loss Rate
             * @default 0
             */
            loss_rate: number;
            /**
             * Lost Deals
             * @default 0
             */
            lost_deals: number;
            /**
             * Lost Reasons
             * @default {}
             */
            lost_reasons: {
                [key: string]: number;
            };
            /**
             * Open Deals
             * @default 0
             */
            open_deals: number;
            /**
             * Pipeline Health Score
             * @default 0
             */
            pipeline_health_score: number;
            /** Pipeline Id */
            pipeline_id?: number | null;
            /**
             * Pipeline Value
             * @default 0
             */
            pipeline_value: number;
            /**
             * Stage Velocity
             * @default []
             */
            stage_velocity: components["schemas"]["StageVelocityOut"][];
            /**
             * Total Deals
             * @default 0
             */
            total_deals: number;
            /**
             * Weighted Pipeline
             * @default 0
             */
            weighted_pipeline: number;
            /**
             * Win Rate
             * @default 0
             */
            win_rate: number;
            /**
             * Won Deals
             * @default 0
             */
            won_deals: number;
            /**
             * Won Reasons
             * @default {}
             */
            won_reasons: {
                [key: string]: number;
            };
        };
        /** RunNowResult */
        RunNowResult: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Run Id */
            run_id?: string | null;
            /** Status */
            status: string;
        };
        /** SalesPerformanceOut */
        SalesPerformanceOut: {
            /**
             * Avg Deal Size
             * @default 0
             */
            avg_deal_size: number;
            /** Avg Sales Cycle Days */
            avg_sales_cycle_days?: number | null;
            /**
             * By Industry
             * @default []
             */
            by_industry: components["schemas"]["RevenueByDimensionOut"][];
            /**
             * By Owner
             * @default []
             */
            by_owner: components["schemas"]["RevenueByDimensionOut"][];
            /**
             * By Region
             * @default []
             */
            by_region: components["schemas"]["RevenueByDimensionOut"][];
            /**
             * By Team
             * @default []
             */
            by_team: components["schemas"]["RevenueByDimensionOut"][];
            /**
             * By Tier
             * @default []
             */
            by_tier: components["schemas"]["RevenueByDimensionOut"][];
            /**
             * Close Rate
             * @default 0
             */
            close_rate: number;
        };
        /** SavedSearchCreate */
        SavedSearchCreate: {
            /**
             * Is Favorite
             * @default false
             */
            is_favorite: boolean;
            /**
             * Is Shared
             * @default false
             */
            is_shared: boolean;
            /** Name */
            name: string;
            /** Query */
            query: {
                [key: string]: unknown;
            };
        };
        /** SavedSearchOut */
        SavedSearchOut: {
            /** Created At */
            created_at?: string | null;
            /** Id */
            id: number;
            /**
             * Is Favorite
             * @default false
             */
            is_favorite: boolean;
            /**
             * Is Shared
             * @default false
             */
            is_shared: boolean;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Query
             * @default {}
             */
            query: {
                [key: string]: unknown;
            };
            /** Updated At */
            updated_at?: string | null;
        };
        /** SavedSearchPatch */
        SavedSearchPatch: {
            /** Is Favorite */
            is_favorite?: boolean | null;
            /** Is Shared */
            is_shared?: boolean | null;
            /** Name */
            name?: string | null;
            /** Query */
            query?: {
                [key: string]: unknown;
            } | null;
        };
        /** SavedViewCreate */
        SavedViewCreate: {
            /**
             * Columns
             * @default []
             */
            columns: string[];
            /** Entity Type */
            entity_type: string;
            /**
             * Filters
             * @default {}
             */
            filters: {
                [key: string]: unknown;
            };
            /**
             * Grouping
             * @default
             */
            grouping: string;
            /**
             * Is Shared
             * @default false
             */
            is_shared: boolean;
            /** Name */
            name: string;
            /**
             * Search
             * @default
             */
            search: string;
            /**
             * Sort By
             * @default
             */
            sort_by: string;
            /**
             * Sort Dir
             * @default desc
             */
            sort_dir: string;
        };
        /** SavedViewOut */
        SavedViewOut: {
            /**
             * Columns
             * @default []
             */
            columns: string[];
            /** Created At */
            created_at?: string | null;
            /** Entity Type */
            entity_type: string;
            /**
             * Filters
             * @default {}
             */
            filters: {
                [key: string]: unknown;
            };
            /**
             * Grouping
             * @default
             */
            grouping: string;
            /** Id */
            id: number;
            /**
             * Is Shared
             * @default false
             */
            is_shared: boolean;
            /** Name */
            name: string;
            /**
             * Owner Email
             * @default
             */
            owner_email: string;
            /** Owner Id */
            owner_id?: number | null;
            /**
             * Search
             * @default
             */
            search: string;
            /**
             * Sort By
             * @default
             */
            sort_by: string;
            /**
             * Sort Dir
             * @default desc
             */
            sort_dir: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** SavedViewPatch */
        SavedViewPatch: {
            /** Columns */
            columns?: string[] | null;
            /** Filters */
            filters?: {
                [key: string]: unknown;
            } | null;
            /** Grouping */
            grouping?: string | null;
            /** Is Shared */
            is_shared?: boolean | null;
            /** Name */
            name?: string | null;
            /** Search */
            search?: string | null;
            /** Sort By */
            sort_by?: string | null;
            /** Sort Dir */
            sort_dir?: string | null;
        };
        /** ScheduledReportRunOut */
        ScheduledReportRunOut: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Id */
            id: number;
            /**
             * Row Count
             * @default 0
             */
            row_count: number;
            /** Run At */
            run_at?: string | null;
            /** Schedule Id */
            schedule_id: number;
            /** Status */
            status: string;
        };
        /** SchedulerStatusOut */
        SchedulerStatusOut: {
            /**
             * Active Recipient Count
             * @default 0
             */
            active_recipient_count: number;
            /** Enabled */
            enabled: boolean;
            /**
             * Grace Minutes
             * @default 0
             */
            grace_minutes: number;
            /**
             * Is Run In Progress
             * @default false
             */
            is_run_in_progress: boolean;
            last_run?: components["schemas"]["ExecutionOut"] | null;
            /** Next Run */
            next_run?: string | null;
            /**
             * Notify Configured
             * @default false
             */
            notify_configured: boolean;
            /**
             * Notify Mode
             * @default auto
             */
            notify_mode: string;
            /** Running */
            running: boolean;
            /**
             * Schedule Times
             * @default []
             */
            schedule_times: string[];
        };
        /** SearchAnalyticsOut */
        SearchAnalyticsOut: {
            /**
             * Article Usage
             * @default {}
             */
            article_usage: {
                [key: string]: number;
            };
            /**
             * Article Views
             * @default {}
             */
            article_views: {
                [key: string]: number;
            };
            /**
             * Avg Search Response Ms
             * @default 0
             */
            avg_search_response_ms: number;
            /**
             * Popular Records
             * @default {}
             */
            popular_records: {
                [key: string]: number;
            };
            /**
             * Search Volume
             * @default 0
             */
            search_volume: number;
            /**
             * Zero Result Searches
             * @default 0
             */
            zero_result_searches: number;
        };
        /** SearchDashboardOut */
        SearchDashboardOut: {
            /**
             * Avg Response Time Ms
             * @default 0
             */
            avg_response_time_ms: number;
            /**
             * Knowledge Activity
             * @default {}
             */
            knowledge_activity: {
                [key: string]: number;
            };
            /**
             * Popular Searches
             * @default []
             */
            popular_searches: string[];
            /**
             * Recent Searches
             * @default []
             */
            recent_searches: components["schemas"]["SearchHistoryOut"][];
            /**
             * Top Articles
             * @default []
             */
            top_articles: components["schemas"]["KbArticleOut"][];
        };
        /** SearchHistoryOut */
        SearchHistoryOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Entity Types
             * @default []
             */
            entity_types: string[];
            /** Id */
            id: number;
            /**
             * Query Text
             * @default
             */
            query_text: string;
            /**
             * Response Time Ms
             * @default 0
             */
            response_time_ms: number;
            /**
             * Result Count
             * @default 0
             */
            result_count: number;
        };
        /** SearchResponseOut */
        SearchResponseOut: {
            /** Query */
            query: string;
            /**
             * Response Time Ms
             * @default 0
             */
            response_time_ms: number;
            /**
             * Results
             * @default []
             */
            results: components["schemas"]["SearchResultOut"][];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** SearchResultOut */
        SearchResultOut: {
            /** Entity Id */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /**
             * Score
             * @default 0
             */
            score: number;
            /**
             * Snippet
             * @default
             */
            snippet: string;
            /** Title */
            title: string;
        };
        /** SecurityPolicyIn */
        SecurityPolicyIn: {
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Policy Type */
            policy_type: string;
        };
        /** SecurityPolicyOut */
        SecurityPolicyOut: {
            /**
             * Config
             * @default {}
             */
            config: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Policy Type */
            policy_type: string;
            /** Updated At */
            updated_at?: string | null;
            /** Updated By */
            updated_by?: number | null;
        };
        /** SendTimeRecommendationOut */
        SendTimeRecommendationOut: {
            /**
             * Factors
             * @default []
             */
            factors: string[];
            /**
             * Rationale
             * @default
             */
            rationale: string;
            /**
             * Recommended Time
             * Format: date-time
             */
            recommended_time: string;
            /**
             * Timezone Offset
             * @default
             */
            timezone_offset: string;
        };
        /** SequenceStepOut */
        SequenceStepOut: {
            /**
             * Action
             * @default
             */
            action: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** Order */
            order: number;
            /**
             * Rationale
             * @default
             */
            rationale: string;
        };
        /** SlaPolicyCreate */
        SlaPolicyCreate: {
            /**
             * Due Hours
             * @default 24
             */
            due_hours: number;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Escalate After Hours */
            escalate_after_hours?: number | null;
            /** Escalate To User Id */
            escalate_to_user_id?: number | null;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Name */
            name: string;
            /**
             * Trigger Event
             * @default
             */
            trigger_event: string;
        };
        /** SlaPolicyOut */
        SlaPolicyOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Due Hours
             * @default 24
             */
            due_hours: number;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Escalate After Hours */
            escalate_after_hours?: number | null;
            /** Escalate To User Id */
            escalate_to_user_id?: number | null;
            /** Id */
            id: number;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Name */
            name: string;
            /**
             * Trigger Event
             * @default
             */
            trigger_event: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** SlaPolicyPatch */
        SlaPolicyPatch: {
            /** Due Hours */
            due_hours?: number | null;
            /** Escalate After Hours */
            escalate_after_hours?: number | null;
            /** Escalate To User Id */
            escalate_to_user_id?: number | null;
            /** Is Enabled */
            is_enabled?: boolean | null;
            /** Name */
            name?: string | null;
        };
        /** SlaTickResultOut */
        SlaTickResultOut: {
            /**
             * Checked
             * @default 0
             */
            checked: number;
            /**
             * Newly At Risk
             * @default 0
             */
            newly_at_risk: number;
            /**
             * Newly Breached
             * @default 0
             */
            newly_breached: number;
            /**
             * Newly Escalated
             * @default 0
             */
            newly_escalated: number;
        };
        /** SlaTrackerCreate */
        SlaTrackerCreate: {
            /** Due At */
            due_at?: string | null;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Policy Id */
            policy_id: number;
        };
        /** SlaTrackerOut */
        SlaTrackerOut: {
            /** Breached At */
            breached_at?: string | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Due At
             * Format: date-time
             */
            due_at: string;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /** Escalated At */
            escalated_at?: string | null;
            /** Id */
            id: number;
            /** Policy Id */
            policy_id: number;
            /** Resolved At */
            resolved_at?: string | null;
            /** Status */
            status: string;
        };
        /** StageVelocityOut */
        StageVelocityOut: {
            /**
             * Avg Time Days
             * @default 0
             */
            avg_time_days: number;
            /**
             * Conversion Rate
             * @default 0
             */
            conversion_rate: number;
            /**
             * Deals Entered
             * @default 0
             */
            deals_entered: number;
            /**
             * Deals Exited
             * @default 0
             */
            deals_exited: number;
            /** Stage Id */
            stage_id: number;
            /** Stage Name */
            stage_name: string;
            /**
             * Stage Order
             * @default 0
             */
            stage_order: number;
            /**
             * Stage Type
             * @default open
             */
            stage_type: string;
        };
        /** SubjectRecommendationOut */
        SubjectRecommendationOut: {
            /**
             * Confidence
             * @default
             */
            confidence: string;
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Subject */
            subject: string;
        };
        /** SuccessProbabilityOut */
        SuccessProbabilityOut: {
            /**
             * Confidence Level
             * @default
             */
            confidence_level: string;
            /**
             * Factors
             * @default []
             */
            factors: string[];
            /**
             * Probability
             * @default 0
             */
            probability: number;
        };
        /** SystemHealthOut */
        SystemHealthOut: {
            /**
             * Api Usage Total
             * @default 0
             */
            api_usage_total: number;
            /**
             * Integrations
             * @default []
             */
            integrations: components["schemas"]["IntegrationStatusOut"][];
            queue_status: components["schemas"]["QueueStatusOut"];
            /**
             * Scheduler Healthy
             * @default true
             */
            scheduler_healthy: boolean;
            /**
             * Workflow Executions
             * @default 0
             */
            workflow_executions: number;
            /**
             * Workflow Success Rate
             * @default 0
             */
            workflow_success_rate: number;
        };
        /** SystemSettingIn */
        SystemSettingIn: {
            /** Category */
            category: string;
            /** Key */
            key: string;
            /**
             * Value
             * @default {}
             */
            value: {
                [key: string]: unknown;
            };
        };
        /** SystemSettingOut */
        SystemSettingOut: {
            /** Category */
            category: string;
            /** Id */
            id: number;
            /** Key */
            key: string;
            /** Updated At */
            updated_at?: string | null;
            /** Updated By */
            updated_by?: number | null;
            /**
             * Value
             * @default {}
             */
            value: {
                [key: string]: unknown;
            };
        };
        /** TargetAttainmentOut */
        TargetAttainmentOut: {
            /**
             * Actual Amount
             * @default 0
             */
            actual_amount: number;
            /**
             * Attainment Pct
             * @default 0
             */
            attainment_pct: number;
            /**
             * Is Elapsed
             * @default false
             */
            is_elapsed: boolean;
            /**
             * Period End
             * Format: date-time
             */
            period_end: string;
            /**
             * Period Start
             * Format: date-time
             */
            period_start: string;
            /**
             * Target Amount
             * @default 0
             */
            target_amount: number;
            /** Target Id */
            target_id: number;
        };
        /** TeamAnalyticsOut */
        TeamAnalyticsOut: {
            /**
             * Assignment Distribution
             * @default []
             */
            assignment_distribution: components["schemas"]["TeamAssignmentDistRow"][];
            /** Avg Completion Time Hours */
            avg_completion_time_hours?: number | null;
            /**
             * Completed Work
             * @default 0
             */
            completed_work: number;
            /**
             * Open Work
             * @default 0
             */
            open_work: number;
            /**
             * Overdue Work
             * @default 0
             */
            overdue_work: number;
            /**
             * Total Assignments
             * @default 0
             */
            total_assignments: number;
        };
        /** TeamAssignmentDistRow */
        TeamAssignmentDistRow: {
            /**
             * Campaigns
             * @default 0
             */
            campaigns: number;
            /**
             * Deals
             * @default 0
             */
            deals: number;
            /**
             * Meetings
             * @default 0
             */
            meetings: number;
            /**
             * Tasks
             * @default 0
             */
            tasks: number;
            /**
             * Total
             * @default 0
             */
            total: number;
            /**
             * User Email
             * @default
             */
            user_email: string;
            /** User Id */
            user_id: number;
        };
        /** TeamDashboardOut */
        TeamDashboardOut: {
            /**
             * My Active Campaigns
             * @default 0
             */
            my_active_campaigns: number;
            /**
             * My Active Deals
             * @default 0
             */
            my_active_deals: number;
            /**
             * Overdue Tasks Count
             * @default 0
             */
            overdue_tasks_count: number;
            /**
             * Pending Approvals
             * @default 0
             */
            pending_approvals: number;
            /**
             * Tasks Due Count
             * @default 0
             */
            tasks_due_count: number;
            /**
             * Team Completed Tasks
             * @default 0
             */
            team_completed_tasks: number;
            /**
             * Team Open Tasks
             * @default 0
             */
            team_open_tasks: number;
            /**
             * Team Overdue Tasks
             * @default 0
             */
            team_overdue_tasks: number;
            /**
             * Total Assignments
             * @default 0
             */
            total_assignments: number;
            /**
             * Unread Notifications
             * @default 0
             */
            unread_notifications: number;
            /**
             * Upcoming Meetings Count
             * @default 0
             */
            upcoming_meetings_count: number;
        };
        /** TemplateRecommendationOut */
        TemplateRecommendationOut: {
            /**
             * Category
             * @default
             */
            category: string;
            /**
             * Match Score
             * @default 0
             */
            match_score: number;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Template Id */
            template_id: number;
        };
        /** TimelineEventOut */
        TimelineEventOut: {
            /**
             * At
             * @default
             */
            at: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Kind
             * @default
             */
            kind: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** TrainRequest */
        TrainRequest: {
            /**
             * Hyperparameters
             * @default {}
             */
            hyperparameters: {
                [key: string]: unknown;
            };
            /** Window Days */
            window_days?: number | null;
        };
        /** TrainResultOut */
        TrainResultOut: {
            /** Backend */
            backend: string;
            /** Dataset Version */
            dataset_version: string;
            /** Feature Version */
            feature_version: string;
            /** Metrics */
            metrics: {
                [key: string]: unknown;
            };
            /** N Rows */
            n_rows: number;
            /** Negative */
            negative: number;
            /** Positive */
            positive: number;
            /**
             * Status
             * @default draft
             */
            status: string;
            /** Version */
            version: string;
        };
        /** TrendOut */
        TrendOut: {
            /** Growth Rate */
            growth_rate?: number | null;
            /** Metric */
            metric: string;
            /**
             * Points
             * @default []
             */
            points: components["schemas"]["TrendPointOut"][];
        };
        /** TrendPointOut */
        TrendPointOut: {
            /** Period */
            period: string;
            /** Value */
            value: number;
        };
        /** UnifiedTimelineEvent */
        UnifiedTimelineEvent: {
            /**
             * Actor
             * @default
             */
            actor: string;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Event Id */
            event_id: string;
            /** Event Type */
            event_type: string;
            /** Label */
            label: string;
            /**
             * Timestamp
             * Format: date-time
             */
            timestamp: string;
            /** Type */
            type: string;
        };
        /** UserAuditOut */
        UserAuditOut: {
            /** Action */
            action: string;
            /**
             * Actor Email
             * @default
             */
            actor_email: string;
            /** Actor User Id */
            actor_user_id?: number | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Id */
            id: number;
            /**
             * Target Email
             * @default
             */
            target_email: string;
            /** Target User Id */
            target_user_id?: number | null;
        };
        /** UserOut */
        UserOut: {
            /** Created At */
            created_at?: string | null;
            /** Deleted At */
            deleted_at?: string | null;
            /** Email */
            email: string;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /** Id */
            id: number;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /** Last Login At */
            last_login_at?: string | null;
            /** Last Seen At */
            last_seen_at?: string | null;
            /**
             * Login Count
             * @default 0
             */
            login_count: number;
            /**
             * Picture
             * @default
             */
            picture: string;
            /** Role */
            role: string;
            /**
             * Status
             * @default active
             */
            status: string;
        };
        /** UserPatch */
        UserPatch: {
            /** Is Active */
            is_active?: boolean | null;
            /** Role */
            role?: string | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WarehouseRefreshResultOut */
        WarehouseRefreshResultOut: {
            /**
             * Snapshots Created
             * @default 0
             */
            snapshots_created: number;
        };
        /** WebhookCreate */
        WebhookCreate: {
            /** Event Type */
            event_type: string;
            /** Name */
            name: string;
            /**
             * Retry Policy
             * @default {}
             */
            retry_policy: {
                [key: string]: unknown;
            };
            /** Target Url */
            target_url: string;
        };
        /** WebhookCreatedOut */
        WebhookCreatedOut: {
            /** Created At */
            created_at?: string | null;
            /** Event Type */
            event_type: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Retry Policy
             * @default {}
             */
            retry_policy: {
                [key: string]: unknown;
            };
            /** Secret */
            secret: string;
            /** Status */
            status: string;
            /** Target Url */
            target_url: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** WebhookDeliveryOut */
        WebhookDeliveryOut: {
            /**
             * Attempt Count
             * @default 0
             */
            attempt_count: number;
            /** Created At */
            created_at?: string | null;
            /** Delivered At */
            delivered_at?: string | null;
            /**
             * Error Detail
             * @default
             */
            error_detail: string;
            /** Event Type */
            event_type: string;
            /** Id */
            id: number;
            /** Last Attempted At */
            last_attempted_at?: string | null;
            /**
             * Payload
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
            /** Response Code */
            response_code?: number | null;
            /** Status */
            status: string;
            /** Webhook Id */
            webhook_id: number;
            /**
             * Webhook Name
             * @default
             */
            webhook_name: string;
        };
        /** WebhookOut */
        WebhookOut: {
            /** Created At */
            created_at?: string | null;
            /** Event Type */
            event_type: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Retry Policy
             * @default {}
             */
            retry_policy: {
                [key: string]: unknown;
            };
            /** Status */
            status: string;
            /** Target Url */
            target_url: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** WebhookPatch */
        WebhookPatch: {
            /** Name */
            name?: string | null;
            /** Retry Policy */
            retry_policy?: {
                [key: string]: unknown;
            } | null;
            /** Status */
            status?: string | null;
            /** Target Url */
            target_url?: string | null;
        };
        /** WorkQueueOut */
        WorkQueueOut: {
            /**
             * My Campaigns
             * @default []
             */
            my_campaigns: components["schemas"]["CampaignOut"][];
            /**
             * My Deals
             * @default []
             */
            my_deals: components["schemas"]["DealOut"][];
            /**
             * Overdue Tasks
             * @default []
             */
            overdue_tasks: components["schemas"]["OutreachTaskOut"][];
            /**
             * Pending Approvals
             * @default 0
             */
            pending_approvals: number;
            /**
             * Tasks Due
             * @default []
             */
            tasks_due: components["schemas"]["OutreachTaskOut"][];
            /**
             * Unread Notifications
             * @default 0
             */
            unread_notifications: number;
            /**
             * Upcoming Meetings
             * @default []
             */
            upcoming_meetings: components["schemas"]["OutreachMeetingOut"][];
        };
        /** WorkflowAction */
        WorkflowAction: {
            /**
             * Params
             * @default {}
             */
            params: {
                [key: string]: unknown;
            };
            /** Type */
            type: string;
        };
        /** WorkflowActionResult */
        WorkflowActionResult: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /**
             * Ok
             * @default true
             */
            ok: boolean;
            /** Type */
            type: string;
        };
        /** WorkflowAnalyticsOut */
        WorkflowAnalyticsOut: {
            /** Avg Approval Time Hours */
            avg_approval_time_hours?: number | null;
            /**
             * Avg Execution Time Ms
             * @default 0
             */
            avg_execution_time_ms: number;
            /**
             * Execution Count
             * @default 0
             */
            execution_count: number;
            /**
             * Failure Count
             * @default 0
             */
            failure_count: number;
            /**
             * Failure Rate
             * @default 0
             */
            failure_rate: number;
            /**
             * Most Used Workflows
             * @default []
             */
            most_used_workflows: components["schemas"]["WorkflowUsageOut"][];
            /**
             * Sla Compliance Rate
             * @default 0
             */
            sla_compliance_rate: number;
            /**
             * Success Count
             * @default 0
             */
            success_count: number;
            /**
             * Success Rate
             * @default 0
             */
            success_rate: number;
        };
        /** WorkflowConditionGroup */
        WorkflowConditionGroup: {
            /**
             * Logic
             * @default AND
             */
            logic: string;
            /**
             * Rules
             * @default []
             */
            rules: components["schemas"]["WorkflowConditionRule"][];
        };
        /** WorkflowConditionRule */
        WorkflowConditionRule: {
            /** Field */
            field: string;
            /**
             * Op
             * @default eq
             */
            op: string;
            /** Value */
            value?: unknown;
        };
        /** WorkflowConditions */
        WorkflowConditions: {
            /**
             * Groups
             * @default []
             */
            groups: components["schemas"]["WorkflowConditionGroup"][];
            /**
             * Logic
             * @default AND
             */
            logic: string;
        };
        /** WorkflowCreate */
        WorkflowCreate: {
            /**
             * Actions
             * @default []
             */
            actions: components["schemas"]["WorkflowAction"][];
            /**
             * @default {
             *       "groups": [],
             *       "logic": "AND"
             *     }
             */
            conditions: components["schemas"]["WorkflowConditions"];
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Name */
            name: string;
            /**
             * Status
             * @default draft
             */
            status: string;
            /** Trigger Event */
            trigger_event: string;
        };
        /** WorkflowDashboardOut */
        WorkflowDashboardOut: {
            /**
             * Active Workflows
             * @default 0
             */
            active_workflows: number;
            /**
             * Failure Count
             * @default 0
             */
            failure_count: number;
            /**
             * Pending Approvals
             * @default 0
             */
            pending_approvals: number;
            /**
             * Recent Executions
             * @default []
             */
            recent_executions: components["schemas"]["WorkflowExecutionOut"][];
            /**
             * Sla Breaches
             * @default 0
             */
            sla_breaches: number;
            /**
             * Success Rate
             * @default 0
             */
            success_rate: number;
            /**
             * Total Executions
             * @default 0
             */
            total_executions: number;
        };
        /** WorkflowExecutionOut */
        WorkflowExecutionOut: {
            /**
             * Actions Executed
             * @default []
             */
            actions_executed: components["schemas"]["WorkflowActionResult"][];
            /** Completed At */
            completed_at?: string | null;
            /**
             * Duration Ms
             * @default 0
             */
            duration_ms: number;
            /**
             * Entity Id
             * @default
             */
            entity_id: string;
            /**
             * Entity Type
             * @default
             */
            entity_type: string;
            /**
             * Error Detail
             * @default
             */
            error_detail: string;
            /** Id */
            id: number;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Trigger Event */
            trigger_event: string;
            /** Workflow Id */
            workflow_id: number;
            /**
             * Workflow Name
             * @default
             */
            workflow_name: string;
        };
        /** WorkflowOut */
        WorkflowOut: {
            /**
             * Actions
             * @default []
             */
            actions: unknown[];
            /**
             * Conditions
             * @default {}
             */
            conditions: {
                [key: string]: unknown;
            };
            /** Created At */
            created_at?: string | null;
            /** Created By */
            created_by?: number | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: number;
            /**
             * Is Enabled
             * @default true
             */
            is_enabled: boolean;
            /** Name */
            name: string;
            /** Status */
            status: string;
            /** Trigger Event */
            trigger_event: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1
             */
            version: number;
        };
        /** WorkflowPatch */
        WorkflowPatch: {
            /** Actions */
            actions?: components["schemas"]["WorkflowAction"][] | null;
            conditions?: components["schemas"]["WorkflowConditions"] | null;
            /** Description */
            description?: string | null;
            /** Is Enabled */
            is_enabled?: boolean | null;
            /** Name */
            name?: string | null;
            /** Status */
            status?: string | null;
        };
        /** WorkflowUsageOut */
        WorkflowUsageOut: {
            /**
             * Execution Count
             * @default 0
             */
            execution_count: number;
            /** Workflow Id */
            workflow_id: number;
            /** Workflow Name */
            workflow_name: string;
        };
        /** WorkloadEntry */
        WorkloadEntry: {
            /**
             * By Status
             * @default {}
             */
            by_status: {
                [key: string]: number;
            };
            /** Email */
            email: string;
            /**
             * Full Name
             * @default
             */
            full_name: string;
            /**
             * Role
             * @default member
             */
            role: string;
            /**
             * Total
             * @default 0
             */
            total: number;
            /** User Id */
            user_id: number;
        };
        /** WorkloadOut */
        WorkloadOut: {
            /**
             * Unassigned High Grade
             * @default 0
             */
            unassigned_high_grade: number;
            /** Users */
            users: components["schemas"]["WorkloadEntry"][];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_users_admin_users_get: {
        parameters: {
            query?: {
                /** @description pending|active|disabled|rejected|deleted */
                status?: string | null;
                /** @description search by email or name */
                q?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    user_audit_admin_users_audit_get: {
        parameters: {
            query?: {
                user_id?: number | null;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserAuditOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_user_admin_users__user_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                user_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user_admin_users__user_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                user_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_user_admin_users__user_id__approve_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                user_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_user_admin_users__user_id__reject_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                user_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activity_summary_ai_activity__entity_type___entity_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ai_analytics_ai_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_briefings_ai_briefings_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiBriefingOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_briefing_ai_briefings_generate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiBriefingOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    latest_briefing_ai_briefings_latest_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiBriefingOut"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    customer_summary_ai_copilot_customer__account_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deal_summary_ai_copilot_deal__deal_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    executive_summary_ai_copilot_executive_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pipeline_summary_ai_copilot_pipeline__pipeline_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    entity_summary_ai_copilot_summary__entity_type___entity_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiCopilotSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ai_dashboard_ai_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    compute_engagement_ai_engagement_compute_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiGenerationResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_engagement_scores_ai_engagement_scores_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_insights_ai_insights_get: {
        parameters: {
            query?: {
                insight_type?: string | null;
                severity?: string | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_insights_ai_insights_generate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiGenerationResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_insight_ai_insights__insight_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                insight_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AiInsightPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiInsightOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_recommendations_ai_recommendations_get: {
        parameters: {
            query?: {
                recommendation_type?: string | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_recommendations_ai_recommendations_generate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiGenerationResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_recommendation_ai_recommendations__rec_id__complete_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                rec_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiRecommendationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dismiss_recommendation_ai_recommendations__rec_id__dismiss_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                rec_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiRecommendationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_risks_ai_risks_get: {
        parameters: {
            query?: {
                risk_type?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    detect_risks_ai_risks_detect_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiGenerationResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_alerts_alerts_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AlertOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    analytics_coverage_analytics_coverage_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalyticsCoverage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    analytics_summary_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalyticsSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_all_assignments_get: {
        parameters: {
            query?: {
                user_id?: number | null;
                status?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssignmentOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_assignments_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssignmentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssignmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_mine_assignments_mine_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssignmentOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assignable_users_assignments_users_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    workload_assignments_workload_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkloadOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    unassign_assignments__assignment_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                assignment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_assignments__assignment_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                assignment_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssignmentPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssignmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_auth_logout_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    me_auth_me_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    microsoft_auth_microsoft_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MicrosoftAuthBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_auth_refresh_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bi_analytics_bi_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BiAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bi_dashboard_bi_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BiDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    executive_dashboard_bi_dashboards__dashboard_type__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dashboard_type: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BiExecutiveDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_kpis_bi_kpis_get: {
        parameters: {
            query?: {
                category?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KpiOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_kpi_bi_kpis_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KpiCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KpiOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_kpi_bi_kpis__kpi_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                kpi_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_kpi_bi_kpis__kpi_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                kpi_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KpiPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KpiOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    kpi_history_bi_kpis__kpi_id__values_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                kpi_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KpiValueOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    record_kpi_value_bi_kpis__kpi_id__values_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                kpi_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KpiValueIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KpiValueOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_reports_bi_reports_get: {
        parameters: {
            query?: {
                owner_id?: number | null;
                status?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomReportOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_report_bi_reports_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomReportCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_report_bi_reports__report_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_report_bi_reports__report_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomReportPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_report_bi_reports__report_id__run_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomReportResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_schedule_bi_reports__report_id__schedules_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReportScheduleCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReportScheduleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_schedules_bi_schedules_get: {
        parameters: {
            query?: {
                report_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReportScheduleOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_due_schedules_bi_schedules_tick_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_schedule_bi_schedules__schedule_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                schedule_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_schedule_bi_schedules__schedule_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                schedule_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReportSchedulePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReportScheduleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deliver_schedule_bi_schedules__schedule_id__deliver_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                schedule_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduledReportRunOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_runs_bi_schedules__schedule_id__runs_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                schedule_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduledReportRunOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_trend_bi_trends__metric__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                metric: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TrendOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_warehouse_bi_warehouse_refresh_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WarehouseRefreshResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_snapshots_bi_warehouse_snapshots_get: {
        parameters: {
            query?: {
                metric_type?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_campaigns_campaigns_get: {
        parameters: {
            query?: {
                owner_id?: number | null;
                status?: string | null;
                campaign_type?: string | null;
                company_domain?: string | null;
                decision_maker_id?: number | null;
                tag?: string | null;
                search?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_campaign_campaigns_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CampaignCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_dashboard_campaigns_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_campaign_campaigns__campaign_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_campaign_campaigns__campaign_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_campaign_campaigns__campaign_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CampaignPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_analytics_campaigns__campaign_id__analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_members_campaigns__campaign_id__members_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_member_campaigns__campaign_id__members_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CampaignMemberIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignMemberOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_member_campaigns__campaign_id__members__member_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
                member_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_member_campaigns__campaign_id__members__member_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
                member_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CampaignMemberPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignMemberOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    enroll_member_campaigns__campaign_id__members__member_id__enroll_post: {
        parameters: {
            query: {
                sequence_id: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
                member_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_timeline_campaigns__campaign_id__timeline_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                campaign_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnifiedTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_companies_companies_get: {
        parameters: {
            query?: {
                /** @description Search by company name (substring, case-insensitive) */
                q?: string | null;
                /** @description Search by company_domain (substring) */
                domain?: string | null;
                /** @description Filter by company_tier */
                tier?: string | null;
                /** @description Filter by prospect_type */
                prospect_type?: string | null;
                /** @description Filter by lead grade (A+/A/B/C) */
                grade?: string | null;
                /** @description Sort field: company_name, company_domain, company_tier, created_at, lead_score */
                sort?: string;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
                /** @description asc or desc */
                order?: string;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_CompanySummary_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_profile_companies__domain__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                /** @description company_domain, e.g. tenstorrent.com */
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyProfile"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activity_companies__domain__activity_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActivityItem"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_notes_companies__domain__notes_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyNoteOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_note_companies__domain__notes_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompanyNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyNoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_accounts_cs_accounts_get: {
        parameters: {
            query?: {
                status?: string | null;
                tier?: string | null;
                lifecycle_stage?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_account_cs_accounts_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsAccountCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_account_cs_accounts__account_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_account_cs_accounts__account_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_account_cs_accounts__account_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsAccountPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_contacts_cs_accounts__account_id__contacts_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsContactOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_health_cs_accounts__account_id__health_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsHealthScoreOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    score_account_cs_accounts__account_id__health_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsHealthScoreCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsHealthScoreOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_history_cs_accounts__account_id__health_history_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsHealthScoreOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lifecycle_history_cs_accounts__account_id__lifecycle_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsLifecycleEventOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_plans_cs_accounts__account_id__plans_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsSuccessPlanOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_risks_cs_accounts__account_id__risks_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsRiskOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    account_timeline_cs_accounts__account_id__timeline_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                account_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cs_analytics_cs_analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_contact_cs_contacts_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsContactCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsContactOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_contact_cs_contacts__contact_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                contact_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_contact_cs_contacts__contact_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                contact_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsContactPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsContactOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_contracts_cs_contracts_get: {
        parameters: {
            query?: {
                account_id?: number | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_contract_cs_contracts_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsContractCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsContractOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_contract_cs_contracts__contract_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                contract_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_contract_cs_contracts__contract_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                contract_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsContractPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsContractOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cs_dashboard_cs_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_milestone_cs_milestones_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsMilestoneCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsMilestoneOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_milestone_cs_milestones__milestone_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                milestone_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_milestone_cs_milestones__milestone_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                milestone_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsMilestonePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsMilestoneOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_plan_cs_plans_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsSuccessPlanCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsSuccessPlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_plan_cs_plans__plan_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                plan_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_plan_cs_plans__plan_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                plan_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsSuccessPlanPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsSuccessPlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_milestones_cs_plans__plan_id__milestones_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                plan_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsMilestoneOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_risk_cs_risks_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsRiskCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsRiskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_risk_cs_risks__risk_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                risk_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_risk_cs_risks__risk_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                risk_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsRiskPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CsRiskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_objects_custom_objects_get: {
        parameters: {
            query?: {
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_object_custom_objects_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomObjectCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomObjectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    object_dashboard_custom_objects_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomObjectDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_field_custom_objects_fields__field_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                field_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_field_custom_objects_fields__field_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                field_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomFieldPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFieldOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_form_custom_objects_forms__form_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                form_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_form_custom_objects_forms__form_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                form_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomFormPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFormOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_object_custom_objects__object_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomObjectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_object_custom_objects__object_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_object_custom_objects__object_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomObjectPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomObjectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    object_analytics_custom_objects__object_id__analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomObjectAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_records_custom_objects__object_id__export_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_fields_custom_objects__object_id__fields_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFieldOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_field_custom_objects__object_id__fields_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomFieldCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFieldOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_forms_custom_objects__object_id__forms_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFormOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_form_custom_objects__object_id__forms_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomFormCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomFormOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_records_custom_objects__object_id__import_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomDataJobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_data_jobs_custom_objects__object_id__jobs_get: {
        parameters: {
            query?: {
                job_type?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomDataJobOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_records_custom_objects__object_id__records_get: {
        parameters: {
            query?: {
                search?: string | null;
                sort_by?: string | null;
                sort_dir?: string;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_record_custom_objects__object_id__records_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomRecordCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomRecordOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_record_custom_objects__object_id__records__record_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
                record_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomRecordOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_record_custom_objects__object_id__records__record_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
                record_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_record_custom_objects__object_id__records__record_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
                record_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CustomRecordPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomRecordOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    record_audit_history_custom_objects__object_id__records__record_id__audit_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
                record_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomRecordAuditOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    related_records_custom_objects__object_id__records__record_id__related_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                object_id: number;
                record_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: components["schemas"]["CustomRecordOut"][];
                    };
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_deals_deals_get: {
        parameters: {
            query?: {
                pipeline_id?: number | null;
                stage_id?: number | null;
                owner_id?: number | null;
                company_domain?: string | null;
                forecast_category?: string | null;
                search?: string | null;
                closing_before?: string | null;
                closing_after?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_deal_deals_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DealCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_deal_deals__deal_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_deal_deals__deal_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_deal_deals__deal_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DealPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deal_history_deals__deal_id__history_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealStageHistoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deal_intelligence_deals__deal_id__intelligence_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealIntelligenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    move_deal_deals__deal_id__move_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DealMoveIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deal_timeline_deals__deal_id__timeline_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                deal_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnifiedTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_decision_makers_decision_makers_get: {
        parameters: {
            query?: {
                /** @description Filter by company */
                company_domain?: string | null;
                /** @description Filter by seniority (e.g. 'senior') */
                seniority?: string | null;
                /** @description Only senior leadership (CxO / founder / VP / director) */
                senior?: boolean;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_DecisionMakerOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decision_maker_companies_decision_makers_companies_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionMakerCompanies"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_contacts_decision_makers_company__domain__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyContactsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_intelligence_decision_makers_company__domain__intelligence_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyIntelligenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_relationships_decision_makers_company__domain__relationships_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyRelationshipsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_decision_maker_decision_makers__dm_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionMakerDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_contact_decision_makers__dm_id__contact_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactOut"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    put_contact_decision_makers__dm_id__contact_put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContactIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_notes_decision_makers__dm_id__notes_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionMakerNoteOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_note_decision_makers__dm_id__notes_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionMakerNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionMakerNoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_note_decision_makers__dm_id__notes__note_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
                note_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_note_decision_makers__dm_id__notes__note_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
                note_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionMakerNoteUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionMakerNoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_demand_signals_demand_signals_get: {
        parameters: {
            query?: {
                /** @description demand_score >= this value */
                min_demand_score?: number | null;
                /** @description Match technologies_detected / primary_focus */
                technology_focus?: string | null;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_DemandSignalOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_enrollments_enrollments_get: {
        parameters: {
            query?: {
                sequence_id?: number | null;
                campaign_id?: number | null;
                status?: string | null;
                search?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    advance_enrollments__enrollment_id__advance_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                enrollment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_enrollments__enrollment_id__cancel_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                enrollment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pause_enrollments__enrollment_id__pause_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                enrollment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resume_enrollments__enrollment_id__resume_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                enrollment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    skip_step_enrollments__enrollment_id__steps__step_id__skip_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                enrollment_id: number;
                step_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmEnrollmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    admin_analytics_governance_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_api_keys_governance_api_keys_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_api_key_governance_api_keys_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApiKeyCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_api_key_governance_api_keys__key_id__revoke_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                key_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rotate_api_key_governance_api_keys__key_id__rotate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                key_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_audit_events_governance_audit_get: {
        parameters: {
            query?: {
                category?: string | null;
                search?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_compliance_records_governance_compliance_get: {
        parameters: {
            query?: {
                record_type?: string | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_compliance_record_governance_compliance_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComplianceRecordCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComplianceRecordOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    soft_delete_entity_governance_compliance_soft_delete__entity_type___entity_id__post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_compliance_record_governance_compliance__record_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                record_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComplianceRecordPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComplianceRecordOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    admin_dashboard_governance_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    system_health_governance_health_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemHealthOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_organizations_governance_organizations_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_organization_governance_organizations_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OrganizationCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_organization_governance_organizations__org_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                org_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_organization_governance_organizations__org_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                org_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OrganizationPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_units_governance_organizations__org_id__units_get: {
        parameters: {
            query?: {
                unit_type?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                org_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrgUnitOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_unit_governance_organizations__org_id__units_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                org_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OrgUnitCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrgUnitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_security_policies_governance_security_policies_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecurityPolicyOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upsert_security_policy_governance_security_policies_put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SecurityPolicyIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecurityPolicyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_settings_governance_settings_get: {
        parameters: {
            query?: {
                category?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemSettingOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upsert_setting_governance_settings_put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SystemSettingIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemSettingOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_member_governance_units_members__member_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                member_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_unit_governance_units__unit_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                unit_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_unit_governance_units__unit_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                unit_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OrgUnitPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrgUnitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_members_governance_units__unit_id__members_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                unit_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrgUnitMemberOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_member_governance_units__unit_id__members_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                unit_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OrgUnitMemberIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrgUnitMemberOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOut"];
                };
            };
        };
    };
    liveness_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    readiness_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    list_integrations_integrations_get: {
        parameters: {
            query?: {
                category?: string | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_integration_integrations_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IntegrationCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    integration_analytics_integrations_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_api_keys_integrations_api_keys_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_connectors_integrations_connectors_get: {
        parameters: {
            query?: {
                connector_type?: string | null;
                status?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_connector_integrations_connectors_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConnectorCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_connector_integrations_connectors__connector_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                connector_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_connector_integrations_connectors__connector_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                connector_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConnectorPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_connector_integrations_connectors__connector_id__run_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                connector_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorRunOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_connector_runs_integrations_connectors__connector_id__runs_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                connector_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorRunOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    integration_dashboard_integrations_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_events_integrations_events_get: {
        parameters: {
            query?: {
                category?: string | null;
                event_type?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_event_integrations_events_publish_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventPublishIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationEventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_oauth_credentials_integrations_oauth_credentials_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OAuthCredentialOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_oauth_credential_integrations_oauth_credentials_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OAuthCredentialCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OAuthCredentialCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_oauth_credential_integrations_oauth_credentials__credential_id__revoke_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                credential_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OAuthCredentialOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rotate_oauth_credential_integrations_oauth_credentials__credential_id__rotate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                credential_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OAuthCredentialCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_plugins_integrations_plugins_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PluginOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    register_plugin_integrations_plugins_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PluginCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PluginOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_plugin_executions_integrations_plugins_executions_list_get: {
        parameters: {
            query?: {
                plugin_id?: number | null;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PluginExecutionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    trigger_plugin_hook_integrations_plugins_hooks__hook_name__trigger_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                hook_name: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PluginExecutionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_plugin_integrations_plugins__plugin_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                plugin_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_plugin_integrations_plugins__plugin_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                plugin_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PluginPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PluginOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_webhooks_integrations_webhooks_get: {
        parameters: {
            query?: {
                event_type?: string | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_webhook_integrations_webhooks_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WebhookCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_deliveries_integrations_webhooks_deliveries_list_get: {
        parameters: {
            query?: {
                webhook_id?: number | null;
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    replay_delivery_integrations_webhooks_deliveries__delivery_id__replay_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                delivery_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookDeliveryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_retry_tick_integrations_webhooks_retry_tick_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_webhook_integrations_webhooks__webhook_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                webhook_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_webhook_integrations_webhooks__webhook_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                webhook_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_webhook_integrations_webhooks__webhook_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                webhook_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WebhookPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_integration_integrations__integration_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                integration_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_integration_integrations__integration_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                integration_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_integration_integrations__integration_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                integration_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IntegrationPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_articles_knowledge_articles_get: {
        parameters: {
            query?: {
                category_id?: number | null;
                status?: string | null;
                owner_id?: number | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_article_knowledge_articles_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KbArticleCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_article_knowledge_articles__article_id__get: {
        parameters: {
            query?: {
                log_view?: boolean;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_article_knowledge_articles__article_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_article_knowledge_articles__article_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KbArticlePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_article_knowledge_articles__article_id__archive_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_attachments_knowledge_articles__article_id__attachments_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbAttachmentOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_attachment_knowledge_articles__article_id__attachments_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KbAttachmentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbAttachmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_article_knowledge_articles__article_id__publish_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    related_articles_knowledge_articles__article_id__related_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RelatedArticleOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_for_approval_knowledge_articles__article_id__submit_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    knowledge_summary_knowledge_articles__article_id__summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KnowledgeSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_versions_knowledge_articles__article_id__versions_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                article_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbArticleVersionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_categories_knowledge_categories_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbCategoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_category_knowledge_categories_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KbCategoryCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbCategoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_category_knowledge_categories__category_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                category_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_category_knowledge_categories__category_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                category_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KbCategoryPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KbCategoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    context_suggestions_knowledge_context_suggestions_get: {
        parameters: {
            query: {
                entity_type: string;
                entity_id: string;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContextSuggestionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_leadership_signals_leadership_signals_get: {
        parameters: {
            query?: {
                /** @description Filter by company */
                company_domain?: string | null;
                /** @description promotion | role_change | new_executive_hire | executive_departure | board_appointment | founder_change | executive_reshuffle */
                movement_type?: string | null;
                /** @description Filter by band (c_level, vp, director, ...) */
                seniority_band?: string | null;
                /** @description linkedin_history | blog_event */
                source?: string | null;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_LeadershipSignalOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_leads_leads_get: {
        parameters: {
            query?: {
                /** @description Filter by grade (A+/A/B/C) */
                grade?: string | null;
                /** @description Filter by company_tier */
                tier?: string | null;
                /** @description Filter by prospect_type */
                prospect_type?: string | null;
                /** @description Ranking: model score · human assessment · combined priority */
                sort?: string;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_LeadOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    build_dataset_ml_dataset_build_post: {
        parameters: {
            query?: {
                window_days?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DatasetBuildResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_features_ml_features_refresh_post: {
        parameters: {
            query?: {
                /** @description Skip companies with unchanged inputs */
                incremental?: boolean;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeatureRefreshResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    feature_vector_ml_features__company_domain__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeatureVectorOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_inference_ml_inference_run_post: {
        parameters: {
            query?: {
                /** @description Model version (default: production) */
                version?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InferenceResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_interactions_ml_interactions_get: {
        parameters: {
            query?: {
                entity_type?: string | null;
                entity_id?: string | null;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InteractionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    record_interaction_ml_interactions_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InteractionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InteractionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_models_ml_models_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MlModelOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_model_ml_models__version__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                version: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MlModelDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    promote_ml_models__version__promote_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                version: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PromotionResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rollback_ml_models__version__rollback_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                version: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PromotionResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_recommendations_ml_recommendations_get: {
        parameters: {
            query?: {
                company_domain?: string | null;
                model_version?: string | null;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecommendationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ml_status_ml_status_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MlStatusOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    train_ml_train_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TrainRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TrainResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_opportunities_opportunities_get: {
        parameters: {
            query?: {
                /** @description Filter by opportunity_type */
                opportunity_type?: string | null;
                /** @description Filter by company */
                company_domain?: string | null;
                /** @description published_date >= (YYYY-MM-DD) */
                date_from?: string | null;
                /** @description published_date <= (YYYY-MM-DD) */
                date_to?: string | null;
                /** @description Filter by lifecycle (NEW/ACTIVE/...) */
                lifecycle_status?: string | null;
                /** @description Hide archived / not-relevant events */
                hide_archived?: boolean;
                /** @description Order: newest | oldest | score (default score) */
                sort?: string | null;
                /** @description Return only ANNUAL_LIST appearances */
                annual_lists_only?: boolean;
                /** @description Return only company-news / people-move entries */
                company_news_only?: boolean;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_OpportunityOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_news_sources_opportunities_news_sources_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NewsSourceOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_news_source_opportunities_news_sources_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewsSourceIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NewsSourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    seed_news_sources_opportunities_news_sources_seed_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NewsSeedResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_news_source_opportunities_news_sources__source_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                source_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewsSourcePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NewsSourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_opportunity_opportunities__opportunity_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_lifecycle_opportunities__opportunity_id__lifecycle_post: {
        parameters: {
            query: {
                /** @description NEW|ACTIVE|MONITORING|RESOLVED|ARCHIVED */
                lifecycle_status: string;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_opportunity_opportunities__opportunity_id__review_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpportunityReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    analytics_outreach_analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachAnalytics"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_analytics_outreach_analytics_company__company_domain__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachAnalyticsDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    template_analytics_outreach_analytics_template__template_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachAnalyticsDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    user_analytics_outreach_analytics_user__user_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                user_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachAnalyticsDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approvals_outreach_approvals_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_campaign_intelligence_outreach_companies__company_domain__intelligence_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CampaignIntelligenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recommend_contacts_outreach_companies__company_domain__recommendations_contacts_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown[];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_priority_outreach_companies__company_domain__recommendations_priority_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachPriorityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recommend_send_time_outreach_companies__company_domain__recommendations_send_time_get: {
        parameters: {
            query?: {
                decision_maker_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SendTimeRecommendationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_sequence_outreach_companies__company_domain__recommendations_sequence_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SequenceStepOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recommend_subjects_outreach_companies__company_domain__recommendations_subjects_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubjectRecommendationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    estimate_success_outreach_companies__company_domain__recommendations_success_probability_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessProbabilityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recommend_templates_outreach_companies__company_domain__recommendations_templates_get: {
        parameters: {
            query?: {
                lead_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                company_domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateRecommendationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    contact_history_outreach_contacts__dm_id__history_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                dm_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactHistoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_conversations_outreach_conversations_get: {
        parameters: {
            query?: {
                folder?: string | null;
                outreach_lead_id?: number | null;
                company_domain?: string | null;
                decision_maker_id?: number | null;
                label_id?: number | null;
                search?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_EmailConversationOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_conversation_action_outreach_conversations_bulk_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkConversationIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BulkOperationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_conversation_outreach_conversations__conv_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_conversation_outreach_conversations__conv_id__archive_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    apply_label_outreach_conversations__conv_id__labels__label_id__post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
                label_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_label_outreach_conversations__conv_id__labels__label_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
                label_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    conversation_messages_outreach_conversations__conv_id__messages_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_conversation_outreach_conversations__conv_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    conversation_timeline_outreach_conversations__conv_id__timeline_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnifiedTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    trash_conversation_outreach_conversations__conv_id__trash_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                conv_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailConversationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dashboard_outreach_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    follow_ups_outreach_follow_ups_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachFollowUpItem"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_auth_url_outreach_gmail_auth_url_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GmailAuthUrlOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_callback_outreach_gmail_callback_get: {
        parameters: {
            query: {
                /** @description Authorization code from Google */
                code: string;
                /** @description CSRF state token */
                state: string;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GmailConnectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_disconnect_outreach_gmail_disconnect_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailProviderAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_refresh_token_outreach_gmail_refresh_token_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GmailRefreshOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_status_outreach_gmail_status_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailProviderAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gmail_sync_outreach_gmail_sync_post: {
        parameters: {
            query?: {
                /** @description Use stored cursor for incremental sync */
                incremental?: boolean;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GmailSyncResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    inbox_outreach_inbox_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachThreadOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_labels_outreach_labels_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailLabelOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_label_outreach_labels_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailLabelIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailLabelOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_label_outreach_labels__label_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                label_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_leads_outreach_leads_get: {
        parameters: {
            query?: {
                stage?: string | null;
                owner_id?: number | null;
                /** @description Only leads owned by the current user */
                mine?: boolean;
                /** @description Only open (active) pipeline stages */
                open_only?: boolean;
                search?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_OutreachLeadOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_lead_outreach_leads_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachLeadCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachLeadDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_from_discovery_outreach_leads_sync_post: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachSyncResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_lead_outreach_leads__lead_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachLeadDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_lead_outreach_leads__lead_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachLeadPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachLeadDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lead_activities_outreach_leads__lead_id__activities_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachActivityOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lead_messages_outreach_leads__lead_id__messages_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_message_outreach_leads__lead_id__messages_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachMessageCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_note_outreach_leads__lead_id__notes_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachActivityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lead_timeline_outreach_leads__lead_id__timeline_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                lead_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnifiedTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_meetings_outreach_meetings_get: {
        parameters: {
            query?: {
                outreach_lead_id?: number | null;
                company_domain?: string | null;
                decision_maker_id?: number | null;
                upcoming_only?: boolean;
                page?: number;
                page_size?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_OutreachMeetingOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_meeting_outreach_meetings_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachMeetingIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMeetingOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_meeting_outreach_meetings__meeting_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                meeting_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMeetingOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_meeting_outreach_meetings__meeting_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                meeting_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_meeting_outreach_meetings__meeting_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                meeting_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachMeetingPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMeetingOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_message_action_outreach_messages_bulk_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkMessageIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BulkOperationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_draft_outreach_messages__message_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_message_outreach_messages__message_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachMessagePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_message_outreach_messages__message_id__approve_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_message_outreach_messages__message_id__archive_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_attachments_outreach_messages__message_id__attachments_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailAttachmentOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_attachment_outreach_messages__message_id__attachments_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailAttachmentIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailAttachmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_attachment_outreach_messages__message_id__attachments__attachment_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
                attachment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailAttachmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_attachment_outreach_messages__message_id__attachments__attachment_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
                attachment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_message_outreach_messages__message_id__cancel_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    duplicate_draft_outreach_messages__message_id__duplicate_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    forward_message_outreach_messages__message_id__forward_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageForwardIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pin_message_outreach_messages__message_id__pin_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    message_preview_outreach_messages__message_id__preview_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessagePreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_read_outreach_messages__message_id__read_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    simulate_reply_outreach_messages__message_id__reply_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reply_to_message_outreach_messages__message_id__reply_draft_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageReplyIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_message_outreach_messages__message_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    schedule_message_outreach_messages__message_id__schedule_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageScheduleIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    send_message_outreach_messages__message_id__send_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    star_message_outreach_messages__message_id__star_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_message_outreach_messages__message_id__submit_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    trash_message_outreach_messages__message_id__trash_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    unpin_message_outreach_messages__message_id__unpin_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_unread_outreach_messages__message_id__unread_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    unstar_message_outreach_messages__message_id__unstar_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                message_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachMessageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_provider_outreach_provider_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailProviderAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_provider_outreach_provider_put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailProviderAccountIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailProviderAccountOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    scheduler_tick_outreach_scheduler_tick_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailSchedulerTickOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    search_messages_outreach_search_get: {
        parameters: {
            query?: {
                q?: string | null;
                company_domain?: string | null;
                decision_maker_id?: number | null;
                status?: string | null;
                folder?: string | null;
                date_from?: string | null;
                date_to?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_OutreachMessageOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_tasks_outreach_tasks_get: {
        parameters: {
            query?: {
                outreach_lead_id?: number | null;
                company_domain?: string | null;
                decision_maker_id?: number | null;
                assigned_to?: number | null;
                mine?: boolean;
                status?: string | null;
                overdue_only?: boolean;
                page?: number;
                page_size?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_OutreachTaskOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_task_outreach_tasks_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachTaskIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTaskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_task_outreach_tasks__task_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTaskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_task_outreach_tasks__task_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_task_outreach_tasks__task_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachTaskPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTaskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_templates_outreach_templates_get: {
        parameters: {
            query?: {
                active_only?: boolean;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTemplateOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_template_outreach_templates_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachTemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTemplateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_template_outreach_templates__template_id__put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutreachTemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutreachTemplateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_template_outreach_templates__template_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                template_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_pipeline_health_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineComponentHealth"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    runs_pipeline_runs_get: {
        parameters: {
            query?: {
                /** @description how many recent runs */
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    status_pipeline_status_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineStatusOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_pipelines_pipelines_get: {
        parameters: {
            query?: {
                active_only?: boolean;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_pipeline_pipelines_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PipelineCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_dashboard_pipelines_dashboard_get: {
        parameters: {
            query?: {
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_pipeline_pipelines__pipeline_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_pipeline_pipelines__pipeline_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_pipeline_pipelines__pipeline_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PipelinePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_analytics_pipelines__pipeline_id__analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DealAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_forecast_pipelines__pipeline_id__forecast_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ForecastOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    kanban_pipelines__pipeline_id__kanban_get: {
        parameters: {
            query?: {
                stage_id?: number | null;
                owner_id?: number | null;
                search?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KanbanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_stage_pipelines__pipeline_id__stages_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PipelineStageCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineStageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_stage_pipelines__pipeline_id__stages__stage_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
                stage_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_stage_pipelines__pipeline_id__stages__stage_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                pipeline_id: number;
                stage_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PipelineStagePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineStageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    production_readiness_platform_config_readiness_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    production_dashboard_platform_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    operational_health_platform_health_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    platform_validate_platform_validate_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_items_review_queue_get: {
        parameters: {
            query?: {
                /** @description pending | approved | rejected | merged */
                status?: string | null;
                source_engine?: string | null;
                match_type?: string | null;
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_ReviewItemOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_item_review_queue__review_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_actions_review_queue__review_id__actions_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewActionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_alias_review_queue__review_id__alias_post: {
        parameters: {
            query?: never;
            header?: {
                "X-Actor"?: string | null;
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AliasBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewActionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_review_queue__review_id__approve_post: {
        parameters: {
            query?: never;
            header?: {
                "X-Actor"?: string | null;
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewActionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    merge_review_queue__review_id__merge_post: {
        parameters: {
            query?: never;
            header?: {
                "X-Actor"?: string | null;
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MergeBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewActionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_review_queue__review_id__reject_post: {
        parameters: {
            query?: never;
            header?: {
                "X-Actor"?: string | null;
                authorization?: string | null;
                "x-api-key"?: string | null;
            };
            path: {
                review_id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RejectBody"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewActionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reports_reviews_reports_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewReports"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_review_reviews__domain__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeadReviewOut"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    put_review_reviews__domain__put: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LeadReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeadReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    history_reviews__domain__history_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                domain: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeadReviewEventOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_bi_summary_revops_bi_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BiSummaryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_executive_dashboard_revops_executive_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExecutiveDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_revenue_forecast_revops_forecast_get: {
        parameters: {
            query?: {
                period_type?: string;
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevenueForecastOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_forecast_accuracy_revops_forecast_accuracy_get: {
        parameters: {
            query?: {
                period_type?: string | null;
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ForecastAccuracyOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_forecast_snapshot_revops_forecast_snapshots_post: {
        parameters: {
            query?: {
                period_type?: string;
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ForecastSnapshotOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_funnel_analytics_revops_funnels_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FunnelAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_pipeline_analytics_revops_pipeline_analytics_get: {
        parameters: {
            query?: {
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevopsPipelineAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_executive_report_revops_reports__report_type__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                report_type: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExecutiveReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_sales_performance_revops_sales_performance_get: {
        parameters: {
            query?: {
                pipeline_id?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SalesPerformanceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_revenue_targets_revops_targets_get: {
        parameters: {
            query?: {
                scope?: string | null;
                owner_id?: number | null;
                period_type?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_revenue_target_revops_targets_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RevenueTargetCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevenueTargetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_revenue_target_revops_targets__target_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                target_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevenueTargetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_revenue_target_revops_targets__target_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                target_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_target_attainment_revops_targets__target_id__attainment_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                target_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TargetAttainmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_now_scheduler_run_now_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunNowResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_runs_scheduler_runs_get: {
        parameters: {
            query?: {
                /** @description 1-based page number */
                page?: number;
                /** @description items per page */
                page_size?: number | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_ExecutionOut_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_run_scheduler_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExecutionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_status_scheduler_status_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SchedulerStatusOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    global_search_search_get: {
        parameters: {
            query?: {
                q?: string;
                entity_types?: string[] | null;
                sort?: string;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    search_analytics_search_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    search_dashboard_search_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    full_text_search_search_full_text_get: {
        parameters: {
            query?: {
                q?: string;
                entity_types?: string[] | null;
                sort?: string;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recent_searches_search_recent_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchHistoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_saved_searches_search_saved_get: {
        parameters: {
            query?: {
                favorites_only?: boolean;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedSearchOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_saved_search_search_saved_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedSearchCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedSearchOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_saved_search_search_saved__search_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                search_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_saved_search_search_saved__search_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                search_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedSearchPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedSearchOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_saved_search_search_saved__search_id__run_post: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                search_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    similar_records_search_similar_records_get: {
        parameters: {
            query: {
                entity_type: string;
                q: string;
                limit?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResultOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_sequences_sequences_get: {
        parameters: {
            query?: {
                active_only?: boolean;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_sequence_sequences_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmSequenceCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmSequenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_sequence_sequences__seq_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmSequenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_sequence_sequences__seq_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_sequence_sequences__seq_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmSequencePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmSequenceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_step_sequences__seq_id__steps_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmSequenceStepIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmSequenceStepOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_step_sequences__seq_id__steps__step_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
                step_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_step_sequences__seq_id__steps__step_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                seq_id: number;
                step_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmSequenceStepPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmSequenceStepOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    workload_analytics_team_analytics_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_assignment_team_assignments_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmAssignmentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmAssignmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_assignment_team_assignments__assignment_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                assignment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_assignment_team_assignments__assignment_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                assignment_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CrmAssignmentPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmAssignmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_entity_assignments_team_assignments__entity_type___entity_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmAssignmentOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assignment_history_team_assignments__entity_type___entity_id__history_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CrmAssignmentHistoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_comment_team_comments__comment_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                comment_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_comment_team_comments__comment_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                comment_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_comments_team_comments__entity_type___entity_id__get: {
        parameters: {
            query?: {
                top_level_only?: boolean;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_comment_team_comments__entity_type___entity_id__post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                entity_type: string;
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    team_dashboard_team_dashboard_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activity_feed_team_feed_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnifiedTimelineEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_notifications_team_notifications_get: {
        parameters: {
            query?: {
                unread_only?: boolean;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_all_read_team_notifications_read_all_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_read_team_notifications__notif_id__read_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                notif_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_saved_views_team_saved_views_get: {
        parameters: {
            query?: {
                entity_type?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_saved_view_team_saved_views_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedViewCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_saved_view_team_saved_views__view_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                view_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_saved_view_team_saved_views__view_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                view_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedViewPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    work_queue_team_work_queue_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkQueueOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_workflows_workflows_get: {
        parameters: {
            query?: {
                status?: string | null;
                trigger_event?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_workflow_workflows_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkflowCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    workflow_analytics_workflows_analytics_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowAnalyticsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_approval_workflows_approvals_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalRequestCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApprovalRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_approvals_workflows_approvals_list_get: {
        parameters: {
            query?: {
                status?: string | null;
                approval_type?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_approval_workflows_approvals__approval_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                approval_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApprovalRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decide_approval_workflows_approvals__approval_id__decide_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                approval_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalDecisionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApprovalRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    workflow_dashboard_workflows_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_executions_workflows_executions_list_get: {
        parameters: {
            query?: {
                workflow_id?: number | null;
                entity_type?: string | null;
                entity_id?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    scan_renewals_workflows_scan_renewals_post: {
        parameters: {
            query?: {
                window_days?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenewalScanResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_sla_policies_workflows_sla_policies_get: {
        parameters: {
            query?: {
                entity_type?: string | null;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaPolicyOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_sla_policy_workflows_sla_policies_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SlaPolicyCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaPolicyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_sla_policy_workflows_sla_policies__policy_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                policy_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SlaPolicyPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaPolicyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sla_tick_workflows_sla_tick_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaTickResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_sla_trackers_workflows_sla_trackers_get: {
        parameters: {
            query?: {
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_sla_tracker_workflows_sla_trackers_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SlaTrackerCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaTrackerOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resolve_sla_tracker_workflows_sla_trackers__tracker_id__resolve_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                tracker_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlaTrackerOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_workflow_workflows__workflow_id__get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                workflow_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_workflow_workflows__workflow_id__delete: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                workflow_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_workflow_workflows__workflow_id__patch: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
                "x-dev-role"?: string | null;
            };
            path: {
                workflow_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkflowPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
