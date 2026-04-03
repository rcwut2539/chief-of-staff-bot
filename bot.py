
import logging
import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API client
client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Bot persona and responsibilities in Thai
BOT_PERSONA = """
# ROLE: Chief of Staff AI

## ตัวตนของคุณ
คุณคือเลขาใหญ่และผู้ประสานงานหลักของบริษัท E-commerce คุณทำงานโดยตรงกับ CEO และมีหน้าที่ดูแลภาพรวมของทีม AI ทั้งหมด

## หน้าที่หลัก
- รับ Brief จาก CEO แล้วแจกงานให้ Agent ที่เหมาะสม
- สรุป Daily Report ส่ง CEO ทุกเช้า 06:00 น.
- ติดตามความคืบหน้าของงานแต่ละทีม
- แจ้งเตือนเรื่องด่วนหรือปัญหาที่ต้องการการตัดสินใจจาก CEO
- จัดลำดับความสำคัญของงานประจำวัน

## วิธีการทำงาน
1. เมื่อรับคำสั่งจาก CEO → สรุปให้ชัดเจนก่อนดำเนินการ
2. ระบุว่างานนี้ควรส่งต่อให้ Agent ใด
3. รายงานผลกลับใน format: สิ่งที่ทำ / สิ่งที่รอดำเนินการ / สิ่งที่ต้องการการตัดสินใจ

## โทนการสื่อสาร
- มืออาชีพ กระชับ ตรงประเด็น
- ใช้ภาษาไทยเป็นหลัก
- รายงานเป็น Bullet Point เสมอ
- ไม่พูดฟุ่มเฟือย

## สิ่งที่ห้ามทำ
- ห้ามตัดสินใจเรื่องสำคัญโดยไม่ถาม CEO
- ห้ามส่งข้อมูลลับของบริษัทออกภายนอก
"""

# File to store tasks
TASKS_FILE = 'tasks.json'

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

# --- Command Handlers ---

async def start(update: Update, context) -> None:
    user = update.effective_user
    welcome_message = (
        f"สวัสดีครับท่าน CEO {user.mention_html()}!\n\n"
        "ผมคือเลขาใหญ่และผู้ประสานงานหลักของบริษัท E-commerce พร้อมรับใช้ครับ\n"
        "หากมีคำสั่งหรือต้องการให้ผมดำเนินการใดๆ โปรดแจ้งได้เลยครับ"
    )
    await update.message.reply_html(welcome_message)

async def brief(update: Update, context) -> None:
    if not context.args:
        await update.message.reply_text(
            "ท่าน CEO ครับ โปรดระบุรายละเอียดของงานด้วยครับ\n"
            "ตัวอย่าง: /brief ตรวจสอบสถานะโปรเจกต์ X และรายงานความคืบหน้า"
        )
        return

    task_description = ' '.join(context.args)
    tasks = load_tasks()
    new_task = {
        'id': len(tasks) + 1,
        'description': task_description,
        'status': 'pending',
        'assigned_to': 'unassigned',
        'created_at': datetime.now().isoformat()
    }
    tasks.append(new_task)
    save_tasks(tasks)

    await update.message.reply_text(
        f"รับทราบครับท่าน CEO! ผมได้บันทึกงาน \"{task_description}\" แล้วครับ\n"
        f"งานนี้ได้รับมอบหมายเป็นงานที่ {new_task['id']} ครับ"
    )

async def tasks(update: Update, context) -> None:
    tasks = load_tasks()
    if not tasks:
        await update.message.reply_text("ท่าน CEO ครับ ตอนนี้ยังไม่มีงานที่ต้องดำเนินการครับ")
        return

    task_list = "ท่าน CEO ครับ นี่คืองานที่อยู่ในระบบครับ:\n\n"
    for task in tasks:
        task_list += (
            f"ID: {task['id']}\n"
            f"รายละเอียด: {task['description']}\n"
            f"สถานะ: {task['status']}\n"
            f"ผู้รับผิดชอบ: {task['assigned_to']}\n"
            f"สร้างเมื่อ: {datetime.fromisoformat(task['created_at']).strftime('%Y-%m-%d %H:%M:%S')}\n"
            "---\n"
        )
    await update.message.reply_text(task_list)

async def report(update: Update, context) -> None:
    tasks = load_tasks()
    pending_tasks = [t for t in tasks if t['status'] == 'pending']
    completed_tasks = [t for t in tasks if t['status'] == 'completed']

    report_text = "ท่าน CEO ครับ รายงานประจำวัน ณ ตอนนี้:\n\n"
    report_text += f"งานที่รอดำเนินการ: {len(pending_tasks)} รายการ\n"
    for task in pending_tasks:
        report_text += f"- ID {task['id']}: {task['description']}\n"

    report_text += f"\nงานที่เสร็จสิ้น: {len(completed_tasks)} รายการ\n"
    for task in completed_tasks:
        report_text += f"- ID {task['id']}: {task['description']}\n"

    if not pending_tasks and not completed_tasks:
        report_text += "ยังไม่มีงานที่บันทึกไว้ครับ"

    await update.message.reply_text(report_text)

async def llm_response(update: Update, context) -> None:
    user_message = update.message.text
    logger.info(f"User message: {user_message}")

    try:
        # Prepare the conversation history for the LLM
        messages = [
            {"role": "system", "content": BOT_PERSONA},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # Using a suitable model, can be changed based on availability
            messages=messages,
            temperature=0.7,
            max_tokens=200,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        bot_reply = response.choices[0].message.content
        await update.message.reply_text(bot_reply)
    except Exception as e:
        logger.error(f"Error communicating with LLM: {e}")
        await update.message.reply_text(
            "ขออภัยครับท่าน CEO เกิดข้อผิดพลาดในการประมวลผลคำสั่งของท่าน โปรดลองอีกครั้งครับ"
        )

def main() -> None:
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set. Please set it before running the bot.")
        return

    application = Application.builder().token(telegram_bot_token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("brief", brief))
    application.add_handler(CommandHandler("tasks", tasks))
    application.add_handler(CommandHandler("report", report))

    # Message handler for LLM responses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, llm_response))

    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
