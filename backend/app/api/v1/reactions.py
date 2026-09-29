from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.chat import ChatConversation, ChatMessage
from app.models.reaction import Reaction
from app.models.ticket import Comment
from app.models.user import User
from app.services import realtime
from app.services.chat_service import short_name
from app.services.permissions import has_perm

router = APIRouter(prefix="/reactions", tags=["reactions"])

EMOJIS = ["👍", "❤️", "😂", "😮", "🙏", "✅", "👀", "🎉"]


class ReactionToggle(BaseModel):
    target_type: str
    target_id: int
    emoji: str


async def _visible_comment(db: AsyncSession, comment_id: int, user: User) -> Comment | None:
    from app.api.v1.tickets import _can_access_ticket
    from app.services import ticket_service
    comment = await db.get(Comment, comment_id)
    if not comment or comment.deleted_at:
        return None
    ticket = await ticket_service.get_ticket(db, comment.ticket_id)
    if not ticket or not (_can_access_ticket(ticket, user) or has_perm(user, "tickets.view_all")):
        return None
    if comment.is_internal and not has_perm(user, "tickets.manage"):
        return None
    if comment.private_to_id and user.id not in comment.private_participants():
        return None
    return comment


async def _visible_ticket(db: AsyncSession, ticket_id: int, user: User):
    """The ticket itself (its description, the first message of the conversation)."""
    from app.api.v1.tickets import _can_access_ticket
    from app.services import ticket_service
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket or not (_can_access_ticket(ticket, user) or has_perm(user, "tickets.view_all")):
        return None
    return ticket


async def _visible_chat_message(db: AsyncSession, message_id: int, user: User) -> ChatMessage | None:
    msg = await db.get(ChatMessage, message_id)
    if not msg:
        return None
    conv = await db.get(ChatConversation, msg.conversation_id)
    if not conv:
        return None
    is_member = any(m.user_id == user.id for m in conv.members)
    if is_member or (conv.kind == "support" and has_perm(user, "chat.support")):
        return msg
    return None


async def _visible_ids(db: AsyncSession, target_type: str, ids: list[int], user: User) -> list[int]:
    check = {"comment": _visible_comment, "ticket": _visible_ticket}.get(target_type, _visible_chat_message)
    return [i for i in ids if await check(db, i, user)]


async def summaries(db: AsyncSession, target_type: str, ids: list[int], user: User) -> dict[int, list[dict]]:
    """{target_id: [{emoji, count, mine, names}]} in the fixed emoji order."""
    if not ids:
        return {}
    rows = (await db.execute(select(Reaction).where(Reaction.target_type == target_type, Reaction.target_id.in_(ids)).order_by(Reaction.id))).scalars().all()
    grouped: dict[int, dict[str, list[Reaction]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[r.target_id][r.emoji].append(r)
    out: dict[int, list[dict]] = {}
    for tid, by_emoji in grouped.items():
        out[tid] = [
            {"emoji": e, "count": len(by_emoji[e]), "mine": any(r.user_id == user.id for r in by_emoji[e]),
             "names": [short_name(r.user.display_name) if r.user else "?" for r in by_emoji[e]]}
            for e in EMOJIS if by_emoji.get(e)
        ]
    return out


@router.get("")
async def list_reactions(target_type: str = Query(...), ids: str = Query(""), db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    if target_type not in ("comment", "chat", "ticket"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo inválido.")
    wanted = [int(x) for x in ids.split(",") if x.strip().isdigit()][:300]
    allowed = await _visible_ids(db, target_type, wanted, current_user)
    data = await summaries(db, target_type, allowed, current_user)
    return {str(i): data.get(i, []) for i in allowed}


@router.post("/toggle")
async def toggle_reaction(data: ReactionToggle, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.target_type not in ("comment", "chat", "ticket") or data.emoji not in EMOJIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reação inválida.")
    if data.target_type == "comment":
        target = await _visible_comment(db, data.target_id, current_user)
    elif data.target_type == "ticket":
        target = await _visible_ticket(db, data.target_id, current_user)
    else:
        target = await _visible_chat_message(db, data.target_id, current_user)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada.")
    existing = (await db.execute(select(Reaction).where(
        Reaction.target_type == data.target_type, Reaction.target_id == data.target_id,
        Reaction.user_id == current_user.id, Reaction.emoji == data.emoji,
    ))).scalar_one_or_none()
    if existing:
        await db.delete(existing)
    else:
        db.add(Reaction(target_type=data.target_type, target_id=data.target_id, user_id=current_user.id, emoji=data.emoji))
    await db.commit()

    # Tell the others to reload the reactions of this message (they fetch them through the permission checks above)
    event = {"type": "reaction.changed", "target_type": data.target_type, "target_id": data.target_id}
    if data.target_type in ("comment", "ticket"):
        ticket_id = target.ticket_id if data.target_type == "comment" else target.id
        event["ticket_id"] = ticket_id
        realtime.publish(realtime.ticket_viewers(ticket_id) - {current_user.id}, event)
    else:
        from app.services.chat_service import member_ids
        event["conversation_id"] = target.conversation_id
        realtime.publish(await member_ids(db, target.conversation_id) - {current_user.id}, event)
    return (await summaries(db, data.target_type, [data.target_id], current_user)).get(data.target_id, [])
