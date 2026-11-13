from .extensions import db
from .models import Conversation, Message, Participant, User


class UserService:
    """Business service handling user identity and registration."""

    @staticmethod
    def register(username: str, display_name: str | None = None) -> tuple[User, bool]:
        """Registers a user if not exists. Returns (User, was_created)."""
        clean_user = username.strip().lower()
        existing = User.query.filter_by(username=clean_user).first()
        if existing:
            return existing, False

        user = User(username=clean_user, display_name=display_name)
        db.session.add(user)
        db.session.commit()
        return user, True

    @staticmethod
    def get_by_username(username: str) -> User | None:
        """Retrieves user by username."""
        return User.query.filter_by(username=username.strip().lower()).first()

    @staticmethod
    def list_users(limit: int = 100) -> list[User]:
        """Lists registered users."""
        return User.query.order_by(User.username.asc()).limit(limit).all()


class ConversationService:
    """Business service handling conversation lifecycle and transactions."""

    @staticmethod
    def create(title: str, participants: list[str]) -> Conversation:
        """Creates a conversation and associates initial participants in a single transaction."""
        conversation = Conversation(title=title)
        db.session.add(conversation)
        db.session.flush()

        for username in participants:
            clean_name = username.strip().lower()
            UserService.register(clean_name)
            db.session.add(Participant(conversation_id=conversation.id, username=clean_name))

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
        clean_name = username.strip().lower()
        UserService.register(clean_name)

        existing = Participant.query.filter_by(conversation_id=conv_id, username=clean_name).first()
        if existing:
            return existing

        participant = Participant(conversation_id=conv_id, username=clean_name)
        db.session.add(participant)
        db.session.commit()
        return participant

    @staticmethod
    def remove_participant(conv_id: int, username: str) -> bool:
        """Removes a participant from a conversation."""
        participant = Participant.query.filter_by(
            conversation_id=conv_id, username=username.strip().lower()
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
            Participant.query.filter_by(
                conversation_id=conv_id, username=username.strip().lower()
            ).first()
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
            Participant.query.filter_by(username=username.strip().lower())
            .join(Conversation)
            .order_by(Conversation.created_at.desc())
            .all()
        )


class MessageService:
    """Business service handling chat message storage and retrieval."""

    @staticmethod
    def create_message(conv_id: int, sender: str, content: str) -> Message:
        """Persists a new chat message to a conversation."""
        message = Message(
            conversation_id=conv_id,
            sender=sender.strip().lower(),
            content=content,
        )
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

    @staticmethod
    def get_last_messages(conv_id: int, limit: int = 3) -> list[Message]:
        """Retrieves the latest messages for a conversation in chronological order."""
        messages = (
            Message.query.filter_by(conversation_id=conv_id)
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))
