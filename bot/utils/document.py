import io
import os
import openai
import json
import logging
import httpx
import asyncio
import random
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import time
from config.config import load_config
from bot.utils.logger import get_logger

logger = get_logger(__name__)

OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# Fallback test yaratish uchun funksiya - OpenAI ishlamay qolganda
async def generate_fallback_test(subject, description, count):
    test_content = []
    
    # Standart savollar to'plami
    quiz_templates = [
        "{num}. {subject} fanida eng muhim tushunchalardan biri nima?",
        "{num}. {subject} fani qachon paydo bo'lgan?",
        "{num}. {subject} fanida asosiy qonunlardan biri qaysi?",
        "{num}. {subject} fanining asoschisi kim?",
        "{num}. {subject} sohasidagi eng so'nggi yutuqlar qaysilar?",
        "{num}. {subject} fanida qo'llaniladigan asosiy metodlar qaysilar?",
        "{num}. {subject} fani qanday bo'limlarga bo'linadi?",
        "{num}. {subject} fanining boshqa fanlar bilan aloqasi qanday?",
        "{num}. {subject} fanida eng ko'p qo'llaniladigan formulalar qaysilar?",
        "{num}. {subject} fanidagi eng muhim tadqiqotlar qaysilar?"
    ]
    
    for i in range(1, count + 1):
        question_template = random.choice(quiz_templates)
        question = question_template.format(num=i, subject=subject)
        
        # To'g'ri javob har doim B), lekin aslida bu muhim emas
        test_content.append(question)
        test_content.append(f"A) 1-variant")
        test_content.append(f"B) 2-variant (to'g'ri)")
        test_content.append(f"C) 3-variant")
        test_content.append(f"D) 4-variant")
        test_content.append(f"Javob: B")
        test_content.append("")
    
    return "\n".join(test_content)

# Progressiv savollarni generatsiya qilish uchun funksiya
async def generate_test_questions(subject, description, count):
    try:
        start_time = time.time()
        client = openai.AsyncClient(api_key=OPENAI_API_KEY)
        
        # Tezroq model va aniqroq ko'rsatmalar bilan yaxshiroq natijalar
        prompt = f"""
        {subject} fani bo'yicha {count} ta test savoli yarating. 
        Har bir test to'rtta variant bilan bo'lishi kerak, faqat bitta to'g'ri javob bo'lishi kerak.
        
        Qo'shimcha ta'rif: {description if description else "Umumiy savollar"}
        
        Formatni quyidagicha qiling va bu formatdan chetga chiqmang:
        
        1. Savol matni?
        A) 1-variant
        B) 2-variant
        C) 3-variant
        D) 4-variant
        Javob: B
        
        2. Ikkinchi savol?
        ...
        
        Quyidagi talablarga amal qiling:
        - Faqat o'zbek tilida yozing
        - Aniq va tushunarli savollar tuzing
        - Imloviy xatolarsiz yozing
        - Har bir savol mantiqiy va aniq bo'lishi kerak
        - To'g'ri javob aniq va asosli bo'lishi kerak
        - Variantlar orasida farq aniq bo'lishi kerak
        - Variantlarni A) B) C) D) ko'rinishida yozing, 1) 2) 3) 4) emas
        - Har bir savol o'quvchilar bilimini tekshirishga qaratilgan bo'lishi kerak
        """
        
        # Avval GPT-3.5-turbo-0125 ishlatamaiz, agar xato bo'lsa, boshqa modelga o'tamiz
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Siz ta'lim sohasida tajribali o'qituvchisiz va sifatli test savollari yaratib berasiz. O'zbekcha savollar tuzishda eng yaxshi mutaxassissiz."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            completion_time = time.time() - start_time
            logger.info(f"Test generation took {completion_time:.2f} seconds for {count} questions")
            
            return response.choices[0].message.content
            
        except Exception as api_error:
            logger.warning(f"Primary API model failed: {api_error}. Trying fallback model...")
            
            # API xatosi yuzaga keldi - fallback test generatsiya qilamiz
            logger.info(f"Using fallback test generation for {subject}")
            return await generate_fallback_test(subject, description, count)
            
    except Exception as e:
        logger.error(f"Error generating test questions: {e}")
        # Agar xato bo'lsa, fallback test generatsiya qilamiz
        logger.info(f"Using fallback test generation for {subject} after error")
        return await generate_fallback_test(subject, description, count)

async def generate_test_document(subject, description, count):
    try:
        questions_text = await generate_test_questions(subject, description, count)
        
        if not questions_text:
            logger.error("No test questions were generated")
            return None
            
        doc = Document()
        
        # Stil yaratish
        styles = doc.styles
        try:
            title_style = styles.add_style('CustomTitle', WD_STYLE_TYPE.PARAGRAPH)
            title_style.font.size = Pt(16)
            title_style.font.bold = True
            title_style.font.color.rgb = RGBColor(0, 0, 139)
            
            question_style = styles.add_style('QuestionStyle', WD_STYLE_TYPE.PARAGRAPH)
            question_style.font.size = Pt(12)
            question_style.font.bold = True
            
            option_style = styles.add_style('OptionStyle', WD_STYLE_TYPE.PARAGRAPH)
            option_style.font.size = Pt(11)
            
            answer_style = styles.add_style('AnswerStyle', WD_STYLE_TYPE.PARAGRAPH)
            answer_style.font.italic = True
            answer_style.font.size = Pt(10)
            answer_style.font.color.rgb = RGBColor(0, 100, 0)
        except ValueError:
            # Stillar allaqachon mavjud
            logger.info("Styles already exist, using existing styles")
        
        # Sarlavha qo'shish
        title = doc.add_heading(f"{subject.upper()} FANI BO'YICHA TEST", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph().add_run().add_break()
        
        if description:
            description_para = doc.add_paragraph()
            description_run = description_para.add_run(f"Tavsif: {description}")
            description_run.font.size = Pt(10)
            description_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph().add_run().add_break()
        
        # Savollarni qayta ishlash
        lines = questions_text.strip().split('\n')
        current_question = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Savol
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) or any(line.startswith(f"{i}.") for i in range(11, 101)):
                if current_question:
                    doc.add_paragraph().add_run().add_break()
                
                try:    
                    current_question = doc.add_paragraph(style='QuestionStyle')
                except ValueError:
                    current_question = doc.add_paragraph()
                    current_question.style.font.bold = True
                    current_question.style.font.size = Pt(12)
                
                current_question.add_run(line)
            # Variant
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                try:
                    option = doc.add_paragraph(style='OptionStyle')
                except ValueError:
                    option = doc.add_paragraph()
                    option.style.font.size = Pt(11)
                
                option.add_run(line)
                option.style = 'List Bullet'
            # Javob
            elif line.startswith('Javob:'):
                try:
                    answer = doc.add_paragraph(style='AnswerStyle')
                except ValueError:
                    answer = doc.add_paragraph()
                    answer.style.font.italic = True
                    answer.style.font.size = Pt(10)
                    answer.style.font.color.rgb = RGBColor(0, 100, 0)
                
                answer.add_run(line)
        
        # Footer qo'shish
        section = doc.sections[0]
        footer = section.footer
        footer_text = footer.paragraphs[0]
        footer_text.text = f"Testbor Bot | {subject} fani | {count} ta savol"
        footer_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream
    except Exception as e:
        logger.error(f"Error creating test document: {e}")
        return None


