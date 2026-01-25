import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from collections import Counter
from heapq import nlargest
import re

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

class SummarizationService:
    @staticmethod
    def extractive_summary(text: str, ratio: float = 0.3) -> str:
        """Extractive summarization using TF-IDF scoring."""
        sentences = sent_tokenize(text)
        if len(sentences) < 2:
            return text[:500]
        
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalnum() and w not in stop_words]
        
        word_freq = Counter(words)
        total_words = len(words)
        
        sentence_scores = {}
        for sentence in sentences:
            for word in word_tokenize(sentence.lower()):
                if word in word_freq:
                    if sentence not in sentence_scores:
                        sentence_scores[sentence] = word_freq[word] / total_words
                    else:
                        sentence_scores[sentence] += word_freq[word] / total_words
        
        summary_sentences = nlargest(int(len(sentences) * ratio), 
                                   sentence_scores, key=sentence_scores.get)
        
        return ' '.join(summary_sentences)

summarization_service = SummarizationService()
