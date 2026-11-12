from .extensions import db
from .models import Conversation, Message, Participant


class ConversationService:
    """Business service handling conversation lifecycle and transactions."""

    @staticmethod
    def create(title: str, participants: list[str]) -> Conversation:
        """Creates a conversation and associates initial participants in a single transaction."""
        conversation = Conversation(title=title)
        db.session.add(conversation)
        db.session.flush()

        for username in participants:
            db.session.add(Participant(conversation_id=conversation.id, username=username))

        db.session.commit()
        return conversation

    @staticmethod
    def get_by_id(conv_id: int) -> Conversation | None:
        """Retrieves a conversation by primary key."""
        return db.session.get(Conversation, conv_id)

    @staticmethod
    def update_title(conv_id: int, new_title: str) -> Conversation | None:
        """Updates conversation title and persists change."""
        conversation = db.session.get(Conversation, conv_id)
        if conversation:
            conversation.title = new_title
            db.session.commit()
        return conversation

    @staticmethod
    def clear_messages(conv_id: int) -> int:
        """Deletes all messages in a conversation and commits."""
        deleted_count = Message.query.filter_by(conversation_id=conv_id).delete()
        db.session.commit()
        return deleted_count


class ParticipantService:
    """Business service handling conversation participant operations."""

    @staticmethod
    def add_participant(conv_id: int, username: str) -> Participant:
        """Adds a user to a conversation if not already present."""
        existing = Participant.query.filter_by(conversation_id=conv_id, username=username).first()
        if existing:
            return existing

        participant = Participant(conversation_id=conv_id, username=username)
        db.session.add(participant)
        db.session.commit()
        return participant

    @staticmethod
    def remove_participant(conv_id: int, username: str) -> bool:
        """Removes a participant from a conversation."""
        participant = Participant.query.filter_by(
            conversation_id=conv_id, username=username
        ).first()
        if not participant:
            return False

        db.session.delete(participant)
        db.session.commit()
        return True

    @staticmethod
    def is_participant(conv_id: int, username: str) -> bool:
        """Checks if a user is an active participant in a conversation."""
        return (
            Participant.query.filter_by(conversation_id=conv_id, username=username).first()
            is not None
        )

    @staticmethod
    def get_participants(conv_id: int) -> list[Participant]:
        """Returns all participants in a conversation."""
        return (
            Participant.query.filter_by(conversation_id=conv_id)
            .order_by(Participant.joined_at.asc())
            .all()
        )

    @staticmethod
    def list_user_participations(username: str) -> list[Participant]:
        """Lists all conversation participations for a user, ordered by creation date."""
        return (
            Participant.query.filter_by(username=username)
            .join(Conversation)
            .order_by(Conversation.created_at.desc())
            .all()
        )


class MessageService:
    """Business service handling chat message storage and retrieval."""

    @staticmethod
    def create_message(conv_id: int, sender: str, content: str) -> Message:
        """Persists a new chat message to a conversation."""
        message = Message(conversation_id=conv_id, sender=sender, content=content)
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def get_messages(conv_id: int, limit: int = 50) -> list[Message]:
        """Retrieves messages for a conversation ordered chronologically."""
        return (
            Message.query.filter_by(conversation_id=conv_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .all()
        )
