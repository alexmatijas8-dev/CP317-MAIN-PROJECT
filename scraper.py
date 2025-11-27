import PyPDF2
import openai
import json


class SyllabusScraper:

    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text

    def parse_syllabus(self, text, semester_start, semester_end):
        prompt = f"""
        You are a syllabus parser. Extract information from the syllabus and return STRICT JSON.

        SEMESTER DATES:
        - Semester starts: {semester_start}
        - Semester ends: {semester_end}

        GENERAL EXTRACTION RULES:
        ---------------------------------------

        1. DATE & TIME FORMATTING
           - Convert all dates to ISO format.
           - If due TIME is given (e.g., “11:59 PM”), include it:
               YYYY-MM-DDTHH:MM:SS
           - Use 24-hour time.
           - If no time is given → use date only (YYYY-MM-DD).
           - Examples:
               “Due Nov 25 at 11:59 PM” → “2025-11-25T23:59:00”
               “Due Nov 25” → “2025-11-25”
           - If the syllabus refers to “Week X”:
               week_start = semester_start + (X - 1) * 7 days
               week_end   = week_start + 6 days
               Use week_start unless a specific day is clearly stated.
           - If a date cannot be determined → due_date = null.

        2. WEIGHT PARSING
           - Convert all weights to numeric values:
               “20%” → 20
               “twenty percent” → 20

        3. CATEGORY WEIGHT DISTRIBUTION (ENHANCED)
           When a syllabus gives a category weight (e.g., “Participation 15%”):
           - SEARCH THE ENTIRE SYLLABUS for occurrences of events belonging to that
             category, including:
               * quizzes
               * assignments
               * labs
               * exercises
               * activities
               * reports
               * tutorials
           - If multiple matching events exist (even if not numbered):
               Create a separate item for EACH event.
               Divide the category weight evenly among them.
           - Use any explicitly stated dates found anywhere in the syllabus
             (grading section, schedule section, weekly breakdown, etc.).

           EXAMPLE:
           If the syllabus lists “Class Participation 15%”
           and elsewhere states that participation is based on 4 quizzes,
           and the course schedule lists quiz dates:
              - Sept 16
              - Sept 30
              - Oct 21
              - Nov 25
           Then:
              - Output 4 quiz items (Quiz 1, Quiz 2, Quiz 3, Quiz 4)
              - Each with weight = 15 / 4 = 3.75
              - Use the actual quiz dates as due_date
              - notes may be “Counts toward class participation” or null

        4. PLURAL-ASSESSMENT RULE (IMPORTANT)
           If the syllabus refers to an assessment using a **plural noun**
           (e.g., “quizzes”, “labs”, “assignments”, “activities”):
             - ASSUME multiple items exist.
             - Search the entire syllabus for ALL occurrences of that assessment type.
             - If dates appear anywhere, use them.
             - Create one assessment entry per occurrence:
                 Quiz 1, Quiz 2, Quiz 3, ...
             - If a single category weight applies, divide it evenly across all items.

        5. REQUIRED ASSESSMENT IDENTIFICATION
           Identify ALL assessments, explicit or implied:
             - assignments
             - quizzes
             - labs
             - projects
             - midterms
             - finals
             - presentations
             - participation components
             - scheduled in-class quizzes or tests
           Each individual item must be listed separately (Quiz 1, Quiz 2, etc.).

        6. GENERATING ASSESSMENT ITEMS (ENHANCED)
           For each assessment you identify:
              * type → string
              * weight → number
              * due_date → ISO date or null
              * notes → string or null

           Additional rules:
           - Auto-number items if multiple events belong to the same category.
           - If the date for an event appears in the weekly/topic schedule, use that date.
           - If no explicit name exists, infer a reasonable name based on the type.

        7. OUTPUT FORMAT — MUST BE STRICT JSON
        {{
            "course_info": {{
                "course_name": "string",
                "course_code": "string",
                "semester": "string",
                "year": "string",
                "instructor": {{
                    "name": "string",
                    "email": "string"
                }}
            }},
            "assessments": {{
                "breakdown": [
                    {{
                        "type": "string",
                        "weight": number,
                        "due_date": "YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or null",
                        "notes": "string or null"
                    }}
                ],
                "total_weight": number
            }}
        }}

        Return STRICT JSON. No commentary. No extra fields.

        ---------------------------------------
        SYLLABUS TEXT:
        {text}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract structured syllabus data and output STRICT JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def scrape_syllabus(self, pdf_path, semester_start, semester_end):
        text = self.extract_text_from_pdf(pdf_path)
        return self.parse_syllabus(text, semester_start, semester_end)
