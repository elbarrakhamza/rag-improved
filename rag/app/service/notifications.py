import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
from app.core.config import settings
from app.database.postgres_connection import get_pool


async def create_notification(
    user_id: int,
    task_id: str,
    title: str,
    message: str,
    type: str = "info"
):
    """Crée une notification en base de données."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO notifications (user_id, task_id, title, message, type, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                user_id,
                task_id,
                title,
                message,
                type
            )
        logger.info(f"Notification créée pour task {task_id}: {title}")
    except Exception as e:
        logger.error(f"Erreur création notification: {e}")


async def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None
):
    """Envoie un email via SMTP (en arrière-plan)."""
    if not settings.enable_email_notifications:
        return

    def _send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_from
            msg["To"] = to_email

            # Texte brut
            part1 = MIMEText(body, "plain")
            msg.attach(part1)

            if html_body:
                part2 = MIMEText(html_body, "html")
                msg.attach(part2)

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from, [to_email], msg.as_string())

            logger.info(f"Email envoyé à {to_email}: {subject}")
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")

    # Exécuter dans un thread pour ne pas bloquer l'event loop
    await asyncio.to_thread(_send)


async def notify_admin(
    user_id: int,
    task_id: str,
    status: str,
    message: str = None
):
    """
    Envoie une notification web et un email à l'admin.
    """
    # Mapping des statuts vers des titres et types
    status_info = {
        "UPLOADED": ("📤 Upload reçu", "info"),
        "GENERATING_CHUNKS": ("⏳ Génération des chunks", "info"),
        "CHUNKS_GENERATED": ("📝 Chunks générés", "success"),
        "CHUNKS_MODIFIED": ("✏️ Chunks modifiés", "warning"),
        "EMBEDDING_IN_PROGRESS": ("🧠 Embedding en cours", "info"),
        "DB_INSERT_IN_PROGRESS": ("💾 Insertion en base", "info"),
        "COMPLETED": ("✅ Ingestion terminée", "success"),
        "FAILED": ("❌ Échec de l'ingestion", "error"),
        "CANCELLED": ("⛔ Tâche annulée", "warning"),
    }

    title, notif_type = status_info.get(status, (f"Statut: {status}", "info"))
    if message:
        title = f"{title} – {message}"

    # Créer la notification web
    await create_notification(user_id, task_id, title, message or status, notif_type)

    # Email
    if settings.admin_email and settings.enable_email_notifications:
        subject = f"[RAG Admin] {title}"
        body = f"Tâche {task_id}\nStatut: {status}\nMessage: {message or ''}"
        html = f"""
        <html>
        <body>
            <h2>{title}</h2>
            <p><strong>Tâche :</strong> {task_id}</p>
            <p><strong>Statut :</strong> {status}</p>
            <p><strong>Message :</strong> {message or ''}</p>
            <p><a href="https://rag-web.stage.enset.top/tasks">Voir les tâches</a></p>
        </body>
        </html>
        """
        await send_email_notification(settings.admin_email, subject, body, html)