import io
import docx
import g4f
from config.config import load_config, ConfigError
from bot.utils.logger import get_logger

logger = get_logger(__name__)

async def generate_test_document(subject: str, description: str, questions_count: int):
    try:
        config = load_config()

        if not config.llama_api_token:
            logger.error("LlamaAPI token is missing")
            raise ConfigError("LlamaAPI tokeni topilmadi. Iltimos, .env fayliga LLAMA_API_TOKEN qo'shing.")

        prompt = f"Generate a {questions_count}-question multiple-choice test about {subject} in Uzbek language."
        if description:
            prompt += f" The test should focus on: {description}."

        prompt += " Format each question as follows:\n\n1. Question text\nA) Option 1\nB) Option 2\nC) Option 3\nD) Option 4\n\nAlso provide an answer key at the end labeled 'Javoblar kaliti:'"

        logger.info(f"Generating test: {subject}, {questions_count} questions")

        client = g4f.Client(api_key=config.llama_api_token)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        test_content = response.choices[0].message.content

        doc = docx.Document()
        doc.add_heading(f"{subject} bo'yicha test", 0)

        if description:
            desc_para = doc.add_paragraph(f"Mavzu: {description}")
            desc_para.style = 'Subtitle'

        sections = test_content.split("\n\n")

        for section in sections:
            if "Javoblar kaliti" in section or "Answer Key" in section:
                doc.add_heading("Javoblar kaliti", level=1)
                answers_text = section.replace("Javoblar kaliti:", "").replace("Answer Key:", "").strip()
                doc.add_paragraph(answers_text)
            else:
                doc.add_paragraph(section)

        footer = doc.sections[0].footer
        footer_para = footer.paragraphs[0]
        footer_para.text = f"Testbor bot tomonidan yaratildi • {subject} • {questions_count} ta savol"

        file_obj = io.BytesIO()
        doc.save(file_obj)
        file_obj.seek(0)

        logger.info(f"Test document generated successfully: {subject}")
        return file_obj
    except Exception as e:
        logger.error(f"Error generating test document: {e}")
        return None


