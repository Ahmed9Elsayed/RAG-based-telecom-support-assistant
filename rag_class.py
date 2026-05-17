import os
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

DATA_PATH = "./data"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class TelecomRAG:
    def __init__(self):
        print("Initializing Advanced TelecomRAG system...")
        
        # Add these print statements so you know it's not frozen!
        print("🧠 1. Loading the AI Model into RAM...")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        print("✅ Model loaded successfully!")
        
        self.chunks = []
        self.metadata = []
        self.index = None
        self.client = Groq(api_key=GROQ_API_KEY)
        
        print("📂 2. Loading your Markdown files...")
        self.load_data()
        print("🚀 Server is fully ready to accept connections!")


    def load_data(self):
        print("Loading and processing documents...")
        for file in os.listdir(DATA_PATH):
            if file.endswith(".md"):
                with open(os.path.join(DATA_PATH, file), "r", encoding="utf-8") as f:
                    text = f.read()

                doc_chunks = self.chunk_text(text)
                for chunk in doc_chunks:
                    self.chunks.append(chunk)
                    self.metadata.append({"source": file})

        # 1. Build Semantic Index (FAISS)
        embeddings = self.create_embeddings(self.chunks)
        self.index = self.build_faiss_index(embeddings)
        
        # 2. Build Keyword Index (BM25)
        print("Building BM25 Keyword Index...")
        tokenized_chunks = [chunk.split() for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_chunks)
        print("✅ Hybrid Indexing Complete!")

    # ================== CHUNKING ==================
    def chunk_text(self, text):
        paragraphs = re.split(r'\n\s*\n', text.strip())
        chunks, current_chunk = [], ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > 700:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    # ================== EMBEDDINGS & FAISS ==================
    def create_embeddings(self, chunks):
        print("Creating embeddings...")
        embeddings = self.model.encode(chunks, normalize_embeddings=True, show_progress_bar=True)
        return np.array(embeddings).astype("float32")

    def build_faiss_index(self, embeddings):
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        print(f"FAISS ready! Total vectors: {index.ntotal}")
        return index


    def retrieve(self, query, top_k=6):
            print(f"Hybrid Searching for: {query}")
            
            # 1. Semantic Search (FAISS)
            query_emb = self.model.encode([query], normalize_embeddings=True).astype("float32")
            # Fetch extra results to give RRF more data to fuse
            distances, indices = self.index.search(query_emb, top_k * 2) 
            semantic_results = indices[0]
                
            # 2. Keyword Search (BM25)
            tokenized_query = query.split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            # Get top indices for keyword matches
            bm25_indices = np.argsort(bm25_scores)[::-1][:top_k * 2]
            
            # 3. Reciprocal Rank Fusion (RRF)
            rrf_scores = {}
            k_rrf = 60 # Standard RRF constant
            
            # Score Semantic Results
            for rank, doc_idx in enumerate(semantic_results):
                if doc_idx not in rrf_scores:
                    rrf_scores[doc_idx] = 0
                rrf_scores[doc_idx] += 1 / (k_rrf + rank + 1)
                
            # Score Keyword Results
            for rank, doc_idx in enumerate(bm25_indices):
                if bm25_scores[doc_idx] == 0: 
                    continue # Skip if no keywords matched
                if doc_idx not in rrf_scores:
                    rrf_scores[doc_idx] = 0
                rrf_scores[doc_idx] += 1 / (k_rrf + rank + 1)
                
            # Sort all chunks by their final RRF Score
            sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
            
            # Format the top_k results
            results = []
            for idx in sorted_indices[:top_k]:
                results.append({
                    "text": self.chunks[idx],
                    "source": self.metadata[idx]["source"],
                    "score": rrf_scores[idx] 
                })
                
            print(f"Found {len(results)} chunks using Hybrid RRF Search")
            return results

    def route_query(self, query: str):
        q = query.strip().lower()
        
        # 1. Clear Rule-based
        # Fix: Expanded greetings list heavily!
        clear_greetings = ["ازيك", "مرحبا", "hello", "hi", "hey", "صباح الخير", "مساء الخير", "اهلا", "أهلا", "السلام عليكم", "عامل ايه"]
        if any(greeting in q for greeting in clear_greetings) and len(q.split()) <= 5:
            return "chat"
            
        clear_out_of_scope = ["فيلم", "مسلسل", "مطعم", "اكل", "كورة", "ماتش", "سياسة", "انتخابات", "دكتور", "مستشفى", "كهربا", "غاز", "بنك"]
        if any(word in q for word in clear_out_of_scope):
            return "out_of_scope"
            
        clear_ticket = ["اعمل تذكرة", "ارفع تذكرة", "افتح تذكرة", "اعمل تيكت", "ابعت مهندس", "عايز مهندس", "اعمل escalate", "شكوى"]
        if any(phrase in q for phrase in clear_ticket):
            return "ticket"

        # 2. Telecom Keyword Check
        strong_telecom_terms = ["فودافون", "اتصالات", "اورنج", "نت", "انترنت", "شبكة", "خط", "فاتورة", "باقة", "راوتر", "5g", "niletel"]
        has_telecom = any(term in q for term in strong_telecom_terms)
        question_words = ["ازاي", "ايه", "ليه", "امتى", "فين", "مين", "هل", "كيف", "ما هو"]
        is_question = any(word in q for word in question_words)
        
        if has_telecom and is_question:
            return "rag" 
            
        # 3. LLM Fallback for ambiguous cases
        # Fix: Added the "chat" category back to the LLM prompt!
        system_prompt = """أنت نظام تصنيف لشركة NileTel للاتصالات.
        صنف الاستفسار إلى:
        1. "chat" - للتحيات والمحادثات البسيطة (مثل: اهلا، السلام عليكم)
        2. "rag" - أسئلة عن الخدمات، المشاكل التقنية، الفواتير
        3. "out_of_scope" - خارج الاتصالات تماماً
        4. "ticket" - طلب إنشاء تذكرة أو إرسال مهندس
        أجب بكلمة واحدة فقط."""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"استفسار: {query}\nالتصنيف:"}
                ],
                temperature=0.0,
                max_tokens=10,
            )
            classification = response.choices[0].message.content.strip().lower()
            
            # Catch the new "chat" route
            if "chat" in classification: return "chat"
            if "out" in classification: return "out_of_scope"
            if "ticket" in classification: return "ticket"
            return "rag"
        except:
            return "rag"


    def parse_structured_output(self, text):
            answer = text
            needs_action = "NO" # Default to NO to be safe
            
            # Upgraded Regex to catch "Needs Action", "needs_action", "Needs_Action", etc.
            pattern1 = r'(?:needs_?action|Needs Action)\s*[:=]\s*(YES|NO|yes|no|Yes|No)'
            match1 = re.search(pattern1, text, re.IGNORECASE)
            
            if match1:
                needs_action = match1.group(1).upper()
                # Strip the needs_action line from the final text shown to the user
                answer = re.sub(r'.*?(?:needs_?action|Needs Action)\s*[:=]\s*(?:YES|NO|yes|no|Yes|No).*?(\n|$)', '', text, flags=re.IGNORECASE).strip()

            answer = re.sub(r'^answer\s*[:=]', '', answer, flags=re.IGNORECASE).strip()
            return {"answer": answer if answer else text, "needs_action": needs_action}
    

# ================== GENERATE (100% Dynamic & Conversational) ==================
    def generate_answer(self, query, retrieved_results, route):
        
        # 1. Build context ONLY if there are RAG results
        context = ""
        if retrieved_results:
            context = "\n\n".join([f"Source: {r['source']}\n{r['text']}" for r in retrieved_results])

        # 2. Dynamic Instructions based on the Route
        if route == "chat":
            system_instruction = """العميل يقوم بإلقاء التحية أو يتحدث بشكل ودي.
رد عليه بترحيب مهني، طبيعي، وودي باللهجة المصرية كأنك موظف حقيقي في شركة NileTel. اسأله كيف يمكنك مساعدته.
إجباري: اكتب في النهاية needs_action: NO"""

        elif route == "out_of_scope":
            system_instruction = """العميل يسأل عن موضوع خارج نطاق الاتصالات وخدمات الإنترنت.
اعتذر بلباقة، تفاعل مع سؤاله بذكاء، ثم وجهه بلطف إلى أنك مخصص فقط لمشاكل وخدمات NileTel.
إجباري: اكتب في النهاية needs_action: NO"""

        elif route == "ticket":
            system_instruction = """العميل يطلب تصعيد مشكلة، فتح تذكرة، أو يشتكي من عطل ويطلب مهندس.
رد عليه بتعاطف واحترافية. اعتذر عن المشكلة المذكورة في سؤاله، وطمئنه أنه سيتم إنشاء تذكرة دعم فني فوراً لتحويلها للقسم المختص (NOC). لا تخترع أرقام تذاكر.
إجباري: اكتب في النهاية needs_action: YES"""

        else: # route == "rag"
            system_instruction = f"""أنت مساعد دعم فني في شركة NileTel.
استخدم السياق التالي فقط للإجابة على مشكلة العميل التقنية.
السياق: {context}
إذا لم تجد الإجابة، اعتذر بلباقة واعرض المساعدة بطريقة أخرى.
إذا كان العميل يطلب صراحة فتح تذكرة بجانب سؤاله التقني، اكتب needs_action: YES، وإلا اكتب needs_action: NO"""

        # 3. Assemble the final prompt
        prompt = f"""{system_instruction}

سؤال العميل: {query}

قواعد الإجابة:
1. أجب بشكل مختصر، طبيعي، ومهني (2-4 جمل).
2. في نهاية الإجابة، يجب أن تكتب في سطر منفصل حالة التذكرة المذكورة في التعليمات.

الإجابة:"""

        try:
            # We use temperature=0.1 to give it a TINY bit of conversational creativity 
            # while keeping the needs_action formatting strictly robotic.
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            raw_text = response.choices[0].message.content or ""
            parsed = self.parse_structured_output(raw_text)
            
            # Identify sources if they exist
            sources = [r["source"] for r in retrieved_results] if retrieved_results else []
            best_source = max(retrieved_results, key=lambda x: x["score"])["source"] if retrieved_results else "None"

            return {
                "answer": parsed["answer"],
                "needs_action": parsed["needs_action"],
                "sources": sources,
                "displayed_source": best_source
            }
            
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return {
                "answer": "عذراً يا فندم، حصل مشكلة في السيستم. ممكن تحاول تاني؟",
                "needs_action": "NO",
                "sources": [],
                "displayed_source": "Error"
            }

    # ================== PIPELINE (Dramatically Simplified) ==================
    def run_rag_pipeline(self, query):
        print(f"\n{'='*60}\nQuery: {query}")
        
        # 1. Classify the intent
        route = self.route_query(query)
        print(f"Route Selected: {route}")

        # 2. Only search the database if it's an actual technical question
        results = []
        if route == "rag":
            results = self.retrieve(query)

        # 3. Let the LLM handle every single response dynamically!
        return self.generate_answer(query, results, route)