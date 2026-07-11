"""Outreach module API — native, on the platform stack.

All endpoints require a signed-in platform user (``get_current_user`` — under the
dev bypass this is the X-Dev-Role identity). Role gates (admin/manager for
approvals, templates, sync, owner assignment) are enforced in the service layer so
the same endpoint serves members and managers with the right capabilities.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import outreach_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    BulkConversationIn,
    BulkMessageIn,
    BulkOperationOut,
    CampaignIntelligenceOut,
    ContactHistoryOut,
    EmailAttachmentIn,
    EmailAttachmentOut,
    EmailConversationOut,
    EmailLabelIn,
    EmailLabelOut,
    EmailProviderAccountIn,
    EmailProviderAccountOut,
    EmailSchedulerTickOut,
    GmailAuthUrlOut,
    GmailConnectOut,
    GmailRefreshOut,
    GmailSyncResultOut,
    MessageForwardIn,
    MessagePreviewOut,
    MessageReplyIn,
    MessageScheduleIn,
    OutreachActivityOut,
    OutreachAnalytics,
    OutreachAnalyticsDetailOut,
    OutreachDashboardOut,
    OutreachFollowUpItem,
    OutreachLeadCreate,
    OutreachLeadDetail,
    OutreachLeadOut,
    OutreachLeadPatch,
    OutreachMeetingIn,
    OutreachMeetingOut,
    OutreachMeetingPatch,
    OutreachMessageCreate,
    OutreachMessageOut,
    OutreachMessagePatch,
    OutreachNoteIn,
    OutreachPriorityOut,
    OutreachSyncResult,
    OutreachTaskIn,
    OutreachTaskOut,
    OutreachTaskPatch,
    OutreachTemplateIn,
    OutreachTemplateOut,
    OutreachThreadOut,
    Page,
    SendTimeRecommendationOut,
    SequenceStepOut,
    SubjectRecommendationOut,
    SuccessProbabilityOut,
    TemplateRecommendationOut,
    UnifiedTimelineEvent,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/outreach", tags=["outreach"])


# ----------------------------------------------------------------- leads
@router.get("/leads", response_model=Page[OutreachLeadOut], summary="List outreach pipeline leads")
def list_leads(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    stage: str | None = Query(None),
    owner_id: int | None = Query(None),
    mine: bool = Query(False, description="Only leads owned by the current user"),
    open_only: bool = Query(False, description="Only open (active) pipeline stages"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list_leads(session, stage=stage, owner_id=owner_id,
                          mine_user_id=user.id if mine else None,
                          open_only=open_only, search=search, page=page, page_size=page_size)


@router.post("/leads", response_model=OutreachLeadDetail, status_code=status.HTTP_201_CREATED,
             summary="Qualify a company into the outreach pipeline (idempotent)")
def create_lead(payload: OutreachLeadCreate, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return svc.create_lead(session, payload, actor)


@router.post("/leads/sync", response_model=OutreachSyncResult,
             summary="Sync top Discovery leads into the pipeline (admin/manager)")
def sync_from_discovery(session: Session = Depends(get_session),
                        actor: User = Depends(get_current_user),
                        limit: int = Query(40, ge=1, le=200)):
    return svc.sync_from_discovery(session, actor, limit=limit)


@router.get("/leads/{lead_id}", response_model=OutreachLeadDetail, summary="Outreach lead detail")
def get_lead(lead_id: int, session: Session = Depends(get_session),
             _: User = Depends(get_current_user)):
    return svc.get_lead_detail(session, lead_id)


@router.patch("/leads/{lead_id}", response_model=OutreachLeadDetail,
              summary="Update stage / owner / service / next action")
def patch_lead(lead_id: int, payload: OutreachLeadPatch, session: Session = Depends(get_session),
               actor: User = Depends(get_current_user)):
    return svc.patch_lead(session, lead_id, payload, actor)


@router.get("/leads/{lead_id}/activities", response_model=list[OutreachActivityOut],
            summary="Activity timeline for a lead")
def lead_activities(lead_id: int, session: Session = Depends(get_session),
                    _: User = Depends(get_current_user)):
    return svc.list_activities(session, lead_id)


@router.post("/leads/{lead_id}/notes", response_model=OutreachActivityOut,
             status_code=status.HTTP_201_CREATED, summary="Add a note to a lead's activity timeline")
def add_note(lead_id: int, payload: OutreachNoteIn, session: Session = Depends(get_session),
             actor: User = Depends(get_current_user)):
    return svc.add_note(session, lead_id, payload.text, actor)


# ----------------------------------------------------------------- messages
@router.get("/leads/{lead_id}/messages", response_model=list[OutreachMessageOut],
            summary="Messages (drafts + sent + replies) for a lead")
def lead_messages(lead_id: int, session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    return svc.list_messages(session, lead_id, user)


@router.post("/leads/{lead_id}/messages", response_model=OutreachMessageOut,
             status_code=status.HTTP_201_CREATED, summary="Create a draft (optionally from a template)")
def create_message(lead_id: int, payload: OutreachMessageCreate,
                   session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.create_message(session, lead_id, payload, actor)


@router.patch("/messages/{message_id}", response_model=OutreachMessageOut, summary="Edit a draft")
def patch_message(message_id: int, payload: OutreachMessagePatch,
                  session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.update_message(session, message_id, payload, actor)


@router.post("/messages/{message_id}/submit", response_model=OutreachMessageOut,
             summary="Submit a draft for approval")
def submit_message(message_id: int, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.submit_for_approval(session, message_id, actor)


@router.post("/messages/{message_id}/approve", response_model=OutreachMessageOut,
             summary="Approve a pending message (admin/manager)")
def approve_message(message_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.approve_message(session, message_id, actor)


@router.post("/messages/{message_id}/send", response_model=OutreachMessageOut,
             summary="Send an approved message via the configured mailer (admin/manager)")
def send_message(message_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    return svc.send_message(session, message_id, actor)


@router.post("/messages/{message_id}/reply", response_model=OutreachMessageOut,
             summary="Simulate an inbound reply (mock-mail demo)")
def simulate_reply(message_id: int, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.simulate_reply(session, message_id, actor)


# ----------------------------------------------------------------- templates
@router.get("/templates", response_model=list[OutreachTemplateOut], summary="List email templates")
def list_templates(session: Session = Depends(get_session), _: User = Depends(get_current_user),
                   active_only: bool = Query(False)):
    return svc.list_templates(session, active_only=active_only)


@router.post("/templates", response_model=OutreachTemplateOut, status_code=status.HTTP_201_CREATED,
             summary="Create a template (admin/manager)")
def create_template(payload: OutreachTemplateIn, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.create_template(session, payload, actor)


@router.put("/templates/{template_id}", response_model=OutreachTemplateOut,
            summary="Update a template (admin/manager)")
def update_template(template_id: int, payload: OutreachTemplateIn,
                    session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.update_template(session, template_id, payload, actor)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a template (admin/manager)")
def delete_template(template_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    svc.delete_template(session, template_id, actor)


# ----------------------------------------------------------------- approvals / inbox / analytics
@router.get("/approvals", response_model=list[OutreachMessageOut],
            summary="Messages pending approval")
def approvals(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return svc.list_approvals(session, user)


@router.get("/inbox", response_model=list[OutreachThreadOut], summary="Outreach threads + replies")
def inbox(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return svc.list_threads(session, user)


@router.get("/analytics", response_model=OutreachAnalytics, summary="Pipeline funnel + mail metrics")
def analytics(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return svc.analytics(session)


# ----------------------------------------------------------------- dashboard
@router.get("/dashboard", response_model=OutreachDashboardOut, summary="Outreach dashboard widgets")
def dashboard(session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.get_dashboard(session, actor)


# ----------------------------------------------------------------- follow-ups
@router.get("/follow-ups", response_model=list[OutreachFollowUpItem], summary="Upcoming + overdue follow-ups")
def follow_ups(session: Session = Depends(get_session), _: User = Depends(get_current_user),
               limit: int = Query(30, ge=1, le=100)):
    return svc.get_follow_ups(session, limit=limit)


# ----------------------------------------------------------------- unified timeline (per lead)
@router.get("/leads/{lead_id}/timeline", response_model=list[UnifiedTimelineEvent],
            summary="Unified activity + meeting + task timeline for a lead")
def lead_timeline(lead_id: int, session: Session = Depends(get_session),
                  _: User = Depends(get_current_user),
                  limit: int = Query(50, ge=1, le=200)):
    return svc.get_lead_timeline(session, lead_id, limit=limit)


# ----------------------------------------------------------------- tasks
@router.get("/tasks", response_model=Page[OutreachTaskOut], summary="List tasks")
def list_tasks(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
    outreach_lead_id: int | None = Query(None),
    company_domain: str | None = Query(None),
    decision_maker_id: int | None = Query(None),
    assigned_to: int | None = Query(None),
    mine: bool = Query(False),
    status: str | None = Query(None),
    overdue_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list_tasks(
        session, actor,
        outreach_lead_id=outreach_lead_id,
        company_domain=company_domain,
        decision_maker_id=decision_maker_id,
        assigned_to=assigned_to,
        mine=mine,
        status=status,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )


@router.post("/tasks", response_model=OutreachTaskOut, status_code=status.HTTP_201_CREATED,
             summary="Create a task")
def create_task(payload: OutreachTaskIn, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return svc.create_task(session, payload, actor)


@router.get("/tasks/{task_id}", response_model=OutreachTaskOut, summary="Get task detail")
def get_task(task_id: int, session: Session = Depends(get_session),
             _: User = Depends(get_current_user)):
    return svc.get_task_detail(session, task_id)


@router.patch("/tasks/{task_id}", response_model=OutreachTaskOut, summary="Update a task")
def patch_task(task_id: int, payload: OutreachTaskPatch, session: Session = Depends(get_session),
               actor: User = Depends(get_current_user)):
    return svc.patch_task(session, task_id, payload, actor)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(task_id: int, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    svc.delete_task(session, task_id, actor)


# ----------------------------------------------------------------- meetings
@router.get("/meetings", response_model=Page[OutreachMeetingOut], summary="List meetings")
def list_meetings(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
    outreach_lead_id: int | None = Query(None),
    company_domain: str | None = Query(None),
    decision_maker_id: int | None = Query(None),
    upcoming_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list_meetings(
        session,
        outreach_lead_id=outreach_lead_id,
        company_domain=company_domain,
        decision_maker_id=decision_maker_id,
        upcoming_only=upcoming_only,
        page=page,
        page_size=page_size,
    )


@router.post("/meetings", response_model=OutreachMeetingOut, status_code=status.HTTP_201_CREATED,
             summary="Log a meeting or call")
def create_meeting(payload: OutreachMeetingIn, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.create_meeting(session, payload, actor)


@router.get("/meetings/{meeting_id}", response_model=OutreachMeetingOut, summary="Meeting detail")
def get_meeting(meeting_id: int, session: Session = Depends(get_session),
                _: User = Depends(get_current_user)):
    return svc.get_meeting_detail(session, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=OutreachMeetingOut, summary="Update a meeting")
def patch_meeting(meeting_id: int, payload: OutreachMeetingPatch,
                  session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.patch_meeting(session, meeting_id, payload, actor)


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a meeting")
def delete_meeting(meeting_id: int, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    svc.delete_meeting(session, meeting_id, actor)


# ----------------------------------------------------------------- contact history
@router.get("/contacts/{dm_id}/history", response_model=ContactHistoryOut,
            summary="Full contact history for a decision maker")
def contact_history(dm_id: int, session: Session = Depends(get_session),
                    _: User = Depends(get_current_user)):
    return svc.get_contact_history(session, dm_id)


# ----------------------------------------------------------------- Phase 2: draft management
@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a draft (author or manager)")
def delete_draft(message_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    svc.delete_draft(session, message_id, actor)


@router.post("/messages/{message_id}/duplicate", response_model=OutreachMessageOut,
             status_code=status.HTTP_201_CREATED, summary="Duplicate a message as a new draft")
def duplicate_draft(message_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.duplicate_draft(session, message_id, actor)


# ----------------------------------------------------------------- Phase 2: scheduling + cancellation
@router.post("/messages/{message_id}/schedule", response_model=OutreachMessageOut,
             summary="Schedule an approved message for future sending (admin/manager)")
def schedule_message(message_id: int, payload: MessageScheduleIn,
                     session: Session = Depends(get_session),
                     actor: User = Depends(get_current_user)):
    return svc.schedule_message(session, message_id, payload, actor)


@router.post("/messages/{message_id}/cancel", response_model=OutreachMessageOut,
             summary="Cancel a scheduled or queued message (admin/manager)")
def cancel_message(message_id: int, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.cancel_message(session, message_id, actor)


# ----------------------------------------------------------------- Phase 2: attachments
@router.get("/messages/{message_id}/attachments", response_model=list[EmailAttachmentOut],
            summary="List attachments for a message")
def list_attachments(message_id: int, session: Session = Depends(get_session),
                     _: User = Depends(get_current_user)):
    return svc.list_attachments(session, message_id, _)


@router.post("/messages/{message_id}/attachments", response_model=EmailAttachmentOut,
             status_code=status.HTTP_201_CREATED, summary="Upload an attachment (base64)")
def add_attachment(message_id: int, payload: EmailAttachmentIn,
                   session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.add_attachment(session, message_id, payload, actor)


@router.get("/messages/{message_id}/attachments/{attachment_id}",
            response_model=EmailAttachmentOut, summary="Get attachment metadata + content (base64)")
def get_attachment(message_id: int, attachment_id: int,
                   session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.get_attachment(session, message_id, attachment_id, actor)


@router.delete("/messages/{message_id}/attachments/{attachment_id}",
               status_code=status.HTTP_204_NO_CONTENT, summary="Remove an attachment")
def remove_attachment(message_id: int, attachment_id: int,
                      session: Session = Depends(get_session),
                      actor: User = Depends(get_current_user)):
    svc.remove_attachment(session, message_id, attachment_id, actor)


# ----------------------------------------------------------------- Phase 2: provider config
@router.get("/provider", response_model=EmailProviderAccountOut,
            summary="Get current user's email provider config")
def get_provider(session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.get_provider_config(session, actor)


@router.put("/provider", response_model=EmailProviderAccountOut,
            summary="Set email provider config (admin/manager)")
def set_provider(payload: EmailProviderAccountIn, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    return svc.set_provider_config(session, payload, actor)


# ----------------------------------------------------------------- Phase 2: scheduler
@router.post("/scheduler/tick", response_model=EmailSchedulerTickOut,
             summary="Run one scheduler cycle — advance scheduled→queued, cancel overdue (admin/manager)")
def scheduler_tick(session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return svc.run_scheduler_tick(session, actor)


# ================================================================= Phase 3: Conversation & Inbox Engine
# ----------------------------------------------------------------- conversations
@router.get("/conversations", response_model=Page[EmailConversationOut],
            summary="List conversations (folder, search, label aware)")
def list_conversations(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
    folder: str | None = Query(None),
    outreach_lead_id: int | None = Query(None),
    company_domain: str | None = Query(None),
    decision_maker_id: int | None = Query(None),
    label_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list_conversations(
        session, actor,
        folder=folder, outreach_lead_id=outreach_lead_id, company_domain=company_domain,
        decision_maker_id=decision_maker_id, label_id=label_id, search=search,
        page=page, page_size=page_size,
    )


@router.get("/conversations/{conv_id}", response_model=EmailConversationOut,
            summary="Get conversation detail")
def get_conversation(conv_id: int, session: Session = Depends(get_session),
                     actor: User = Depends(get_current_user)):
    return svc.get_conversation(session, conv_id, actor)


@router.get("/conversations/{conv_id}/messages", response_model=list[OutreachMessageOut],
            summary="All messages in a conversation (chronological)")
def conversation_messages(conv_id: int, session: Session = Depends(get_session),
                          actor: User = Depends(get_current_user)):
    return svc.get_conversation_messages(session, conv_id, actor)


@router.get("/conversations/{conv_id}/timeline", response_model=list[UnifiedTimelineEvent],
            summary="Unified email + meeting + task + note timeline for a conversation's lead")
def conversation_timeline(conv_id: int, session: Session = Depends(get_session),
                          actor: User = Depends(get_current_user)):
    return svc.get_conversation_timeline(session, conv_id, actor)


@router.post("/conversations/{conv_id}/archive", response_model=EmailConversationOut,
             summary="Archive a conversation")
def archive_conversation(conv_id: int, session: Session = Depends(get_session),
                         actor: User = Depends(get_current_user)):
    return svc.archive_conversation(session, conv_id, actor)


@router.post("/conversations/{conv_id}/restore", response_model=EmailConversationOut,
             summary="Restore an archived/trashed conversation")
def restore_conversation(conv_id: int, session: Session = Depends(get_session),
                         actor: User = Depends(get_current_user)):
    return svc.restore_conversation(session, conv_id, actor)


@router.post("/conversations/{conv_id}/trash", response_model=EmailConversationOut,
             summary="Move a conversation to trash")
def trash_conversation(conv_id: int, session: Session = Depends(get_session),
                       actor: User = Depends(get_current_user)):
    return svc.trash_conversation(session, conv_id, actor)


# ----------------------------------------------------------------- message state
@router.post("/messages/{message_id}/read", response_model=OutreachMessageOut,
             summary="Mark message as read")
def mark_read(message_id: int, session: Session = Depends(get_session),
              actor: User = Depends(get_current_user)):
    return svc.mark_read(session, message_id, actor)


@router.post("/messages/{message_id}/unread", response_model=OutreachMessageOut,
             summary="Mark message as unread")
def mark_unread(message_id: int, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return svc.mark_unread(session, message_id, actor)


@router.post("/messages/{message_id}/star", response_model=OutreachMessageOut,
             summary="Star a message")
def star_message(message_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    return svc.star_message(session, message_id, actor)


@router.post("/messages/{message_id}/unstar", response_model=OutreachMessageOut,
             summary="Remove star from a message")
def unstar_message(message_id: int, session: Session = Depends(get_session),
                   actor: User = Depends(get_current_user)):
    return svc.unstar_message(session, message_id, actor)


@router.post("/messages/{message_id}/pin", response_model=OutreachMessageOut,
             summary="Pin a message")
def pin_message(message_id: int, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return svc.pin_message(session, message_id, actor)


@router.post("/messages/{message_id}/unpin", response_model=OutreachMessageOut,
             summary="Unpin a message")
def unpin_message(message_id: int, session: Session = Depends(get_session),
                  actor: User = Depends(get_current_user)):
    return svc.unpin_message(session, message_id, actor)


@router.post("/messages/{message_id}/archive", response_model=OutreachMessageOut,
             summary="Archive a message")
def archive_message(message_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.archive_message(session, message_id, actor)


@router.post("/messages/{message_id}/restore", response_model=OutreachMessageOut,
             summary="Restore an archived/trashed message")
def restore_message(message_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.restore_message(session, message_id, actor)


@router.post("/messages/{message_id}/trash", response_model=OutreachMessageOut,
             summary="Move message to trash")
def trash_message(message_id: int, session: Session = Depends(get_session),
                  actor: User = Depends(get_current_user)):
    return svc.trash_message(session, message_id, actor)


# ----------------------------------------------------------------- thread actions
@router.post("/messages/{message_id}/reply-draft", response_model=OutreachMessageOut,
             status_code=status.HTTP_201_CREATED, summary="Create a reply draft from an existing message")
def reply_to_message(message_id: int, payload: MessageReplyIn,
                     session: Session = Depends(get_session),
                     actor: User = Depends(get_current_user)):
    return svc.reply_to_message(session, message_id, payload, actor)


@router.post("/messages/{message_id}/forward", response_model=OutreachMessageOut,
             status_code=status.HTTP_201_CREATED, summary="Create a forward draft from an existing message")
def forward_message(message_id: int, payload: MessageForwardIn,
                    session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.forward_message(session, message_id, payload, actor)


# ----------------------------------------------------------------- preview
@router.get("/messages/{message_id}/preview", response_model=MessagePreviewOut,
            summary="Sanitized message preview (safe HTML + plain text + attachment list)")
def message_preview(message_id: int, session: Session = Depends(get_session),
                    actor: User = Depends(get_current_user)):
    return svc.get_message_preview(session, message_id, actor)


# ----------------------------------------------------------------- search
@router.get("/search", response_model=Page[OutreachMessageOut],
            summary="Search messages (subject, body, sender, recipient, folder, status, date)")
def search_messages(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
    q: str | None = Query(None),
    company_domain: str | None = Query(None),
    decision_maker_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    folder: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    from datetime import datetime
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    return svc.search_messages(
        session, actor,
        q=q, company_domain=company_domain, decision_maker_id=decision_maker_id,
        status=status_filter, folder=folder, date_from=df, date_to=dt,
        page=page, page_size=page_size,
    )


# ----------------------------------------------------------------- labels
@router.get("/labels", response_model=list[EmailLabelOut], summary="List all labels (system + custom)")
def list_labels(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return svc.list_labels(session, _)


@router.post("/labels", response_model=EmailLabelOut, status_code=status.HTTP_201_CREATED,
             summary="Create a custom label (admin/manager)")
def create_label(payload: EmailLabelIn, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    return svc.create_label(session, payload, actor)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a custom label (admin/manager; system labels cannot be deleted)")
def delete_label(label_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    svc.delete_label(session, label_id, actor)


@router.post("/conversations/{conv_id}/labels/{label_id}",
             response_model=EmailConversationOut, summary="Apply a label to a conversation")
def apply_label(conv_id: int, label_id: int, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return svc.apply_label(session, conv_id, label_id, actor)


@router.delete("/conversations/{conv_id}/labels/{label_id}",
               response_model=EmailConversationOut, summary="Remove a label from a conversation")
def remove_label(conv_id: int, label_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(get_current_user)):
    return svc.remove_label(session, conv_id, label_id, actor)


# ----------------------------------------------------------------- bulk operations
@router.post("/messages/bulk", response_model=BulkOperationOut,
             summary="Bulk action on messages (archive|restore|trash|mark_read|mark_unread)")
def bulk_message_action(payload: BulkMessageIn, session: Session = Depends(get_session),
                        actor: User = Depends(get_current_user)):
    return svc.bulk_message_action(session, payload, actor)


@router.post("/conversations/bulk", response_model=BulkOperationOut,
             summary="Bulk action on conversations (archive|restore|trash|apply_label|remove_label)")
def bulk_conversation_action(payload: BulkConversationIn, session: Session = Depends(get_session),
                              actor: User = Depends(get_current_user)):
    return svc.bulk_conversation_action(session, payload, actor)


# ================================================================= Phase 4: Gmail OAuth & Sync

@router.get(
    "/gmail/auth-url",
    response_model=GmailAuthUrlOut,
    summary="Generate Gmail OAuth authorization URL (starts the connect flow)",
)
def gmail_auth_url(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_get_auth_url(session, actor)


@router.get(
    "/gmail/callback",
    response_model=GmailConnectOut,
    summary="Gmail OAuth callback — exchange authorization code for tokens",
)
def gmail_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token"),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_handle_callback(session, actor, code=code, state=state)


@router.get(
    "/gmail/status",
    response_model=EmailProviderAccountOut,
    summary="Gmail connection status for the current user",
)
def gmail_status(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_status(session, actor)


@router.post(
    "/gmail/disconnect",
    response_model=EmailProviderAccountOut,
    summary="Disconnect Gmail — revoke stored tokens",
)
def gmail_disconnect(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_disconnect(session, actor)


@router.post(
    "/gmail/sync",
    response_model=GmailSyncResultOut,
    summary="Trigger a manual Gmail sync for the current user",
)
def gmail_sync(
    incremental: bool = Query(True, description="Use stored cursor for incremental sync"),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_sync(session, actor, incremental=incremental)


@router.post(
    "/gmail/refresh-token",
    response_model=GmailRefreshOut,
    summary="Manually refresh the Gmail access token",
)
def gmail_refresh_token(
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.gmail_refresh_token(session, actor)


# ================================================================= Phase 5: Outreach Intelligence

@router.get(
    "/companies/{company_domain}/recommendations/contacts",
    response_model=list,
    summary="Get ranked contact recommendations for outreach",
)
def recommend_contacts(
    company_domain: str,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_contact_recommendations(session, company_domain)


@router.get(
    "/companies/{company_domain}/recommendations/send-time",
    response_model=SendTimeRecommendationOut,
    summary="Get recommended send time for outreach",
)
def recommend_send_time(
    company_domain: str,
    decision_maker_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_send_time_recommendation(session, company_domain, decision_maker_id)


@router.get(
    "/companies/{company_domain}/recommendations/subjects",
    response_model=list[SubjectRecommendationOut],
    summary="Get recommended email subjects",
)
def recommend_subjects(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_subject_recommendations(session, company_domain, lead_id)


@router.get(
    "/companies/{company_domain}/recommendations/templates",
    response_model=list[TemplateRecommendationOut],
    summary="Get recommended email templates",
)
def recommend_templates(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_template_recommendations(session, company_domain, lead_id)


@router.get(
    "/companies/{company_domain}/recommendations/success-probability",
    response_model=SuccessProbabilityOut,
    summary="Estimate conversion probability",
)
def estimate_success(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_success_probability(session, company_domain, lead_id)


@router.get(
    "/companies/{company_domain}/recommendations/priority",
    response_model=OutreachPriorityOut,
    summary="Get outreach priority classification",
)
def get_priority(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_outreach_priority(session, company_domain, lead_id)


@router.get(
    "/companies/{company_domain}/recommendations/sequence",
    response_model=list[SequenceStepOut],
    summary="Get recommended outreach sequence",
)
def get_sequence(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_outreach_sequence(session, company_domain, lead_id)


@router.get(
    "/companies/{company_domain}/intelligence",
    response_model=CampaignIntelligenceOut,
    summary="Get all outreach intelligence for a company",
)
def get_campaign_intelligence(
    company_domain: str,
    lead_id: int | None = Query(None),
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_campaign_intelligence(session, company_domain, lead_id)


@router.get(
    "/analytics/user/{user_id}",
    response_model=OutreachAnalyticsDetailOut,
    summary="Get per-user outreach analytics",
)
def user_analytics(
    user_id: int,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_user_analytics(session, user_id)


@router.get(
    "/analytics/company/{company_domain}",
    response_model=OutreachAnalyticsDetailOut,
    summary="Get per-company outreach analytics",
)
def company_analytics(
    company_domain: str,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_company_analytics(session, company_domain)


@router.get(
    "/analytics/template/{template_id}",
    response_model=OutreachAnalyticsDetailOut,
    summary="Get per-template outreach analytics",
)
def template_analytics(
    template_id: int,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_user),
):
    return svc.get_template_analytics(session, template_id)
