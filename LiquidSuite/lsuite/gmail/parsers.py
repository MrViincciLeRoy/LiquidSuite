"""
PDF Parser - Extract transactions from bank statement PDFs
"""
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF statement parser"""
    
    def parse_pdf(self, pdf_data, bank_name, password=None):
        """
        Parse PDF and extract transactions
        
        Args:
            pdf_data: Binary PDF data
            bank_name: Bank identifier (tymebank, capitec, other)
            password: PDF password if protected
            
        Returns:
            List of transaction dictionaries
        """
        text = self._extract_text_from_pdf(pdf_data, password)
        
        if bank_name == 'tymebank':
            return self._parse_tymebank(text)
        elif bank_name == 'capitec':
            return self._parse_capitec(text)
        else:
            return self._parse_generic(text)
    
    def _extract_text_from_pdf(self, pdf_data, password=None):
        """Extract text from PDF using available library"""
        text = ""
        
        try:
            # Try PyPDF2 first
            import PyPDF2
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Handle encrypted PDFs
            if pdf_reader.is_encrypted:
                if not password:
                    raise ValueError("PDF is password protected but no password provided")
                
                decrypt_result = pdf_reader.decrypt(password)
                if decrypt_result == 0:
                    raise ValueError("Incorrect PDF password")
            
            # Extract text from all pages
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters using PyPDF2")
            
        except ImportError:
            # Fallback to pdfplumber
            try:
                import pdfplumber
                pdf_file = io.BytesIO(pdf_data)
                
                with pdfplumber.open(pdf_file, password=password) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                
                logger.info(f"Extracted {len(text)} characters using pdfplumber")
                
            except ImportError:
                raise ImportError("No PDF library available. Install PyPDF2 or pdfplumber")
        
        return text
    
    def _parse_tymebank(self, text):
        """Parse TymeBank PDF format"""
        transactions = []
        
        # TymeBank patterns
        patterns = [
            # Pattern: 12 Jan 2024 | Description | -R1,234.56
            (r'(\d{2}\s+\w{3}\s+\d{4})\s*[|\|]\s*([^|\|]+?)\s*[|\|]\s*(-?R?[\d,]+\.\d{2})', '%d %b %Y'),
            # Pattern: 2024-01-12 Description R1234.56
            (r'(\d{4}-\d{2}-\d{2})\s+([^\d\-\+R]+?)\s+(-?R?[\d,]+\.\d{2})', '%Y-%m-%d'),
            # Pattern: 12/01/2024 Description R1234.56
            (r'(\d{2}/\d{2}/\d{4})\s+([^\d\-\+R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
        ]
        
        for pattern, date_format in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            if matches:
                logger.info(f"Found {len(matches)} TymeBank transactions with pattern: {pattern}")
                
                for match in matches:
                    try:
                        trans_date = datetime.strptime(match[0].strip(), date_format).date()
                        description = match[1].strip()
                        amount_str = match[2].replace('R', '').replace(',', '').strip()
                        amount = float(amount_str)
                        
                        transactions.append({
                            'date': trans_date,
                            'description': description,
                            'amount': abs(amount),
                            'type': 'debit' if amount < 0 else 'credit',
                            'reference': f"TYME-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                        })
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse TymeBank transaction: {e}")
                        continue
                
                if transactions:
                    break  # Use first matching pattern
        
        return transactions
    
    def _parse_capitec(self, text):
        """Parse Capitec PDF format"""
        transactions = []
        
        # Capitec patterns
        patterns = [
            # Pattern: 2024/01/12 Description -1234.56
            (r'(\d{4}/\d{2}/\d{2})\s+([^\d\-\+]+?)\s+(-?[\d,]+\.\d{2})', '%Y/%m/%d'),
            # Pattern: 12/01/2024 Description R1234.56
            (r'(\d{2}/\d{2}/\d{4})\s+([^\d\-\+R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            # Pattern: 12 Jan Description -1234.56
            (r'(\d{2}\s+\w{3})\s+([^\d\-\+]+?)\s+(-?[\d,]+\.\d{2})', '%d %b'),
        ]
        
        current_year = datetime.now().year
        
        for pattern, date_format in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            if matches:
                logger.info(f"Found {len(matches)} Capitec transactions with pattern: {pattern}")
                
                for match in matches:
                    try:
                        date_str = match[0].strip()
                        
                        # Handle dates without year
                        if date_format == '%d %b':
                            date_str = f"{date_str} {current_year}"
                            date_format = '%d %b %Y'
                        
                        trans_date = datetime.strptime(date_str, date_format).date()
                        description = match[1].strip()
                        amount_str = match[2].replace('R', '').replace(',', '').strip()
                        amount = float(amount_str)
                        
                        transactions.append({
                            'date': trans_date,
                            'description': description,
                            'amount': abs(amount),
                            'type': 'debit' if amount < 0 else 'credit',
                            'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                        })
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse Capitec transaction: {e}")
                        continue
                
                if transactions:
                    break
        
        return transactions
    
    def _parse_generic(self, text):
        """Generic PDF parsing for unknown banks"""
        transactions = []
        
        # Generic patterns that might work for various banks
        patterns = [
            # Date | Description | Amount
            (r'(\d{2}/\d{2}/\d{4})\s*[|\|]\s*([^|\|]+?)\s*[|\|]\s*(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            # Date Description Amount
            (r'(\d{2}/\d{2}/\d{4})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            # YYYY-MM-DD Description Amount
            (r'(\d{4}-\d{2}-\d{2})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%Y-%m-%d'),
            # DD Mon YYYY Description Amount
            (r'(\d{2}\s+\w{3}\s+\d{4})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d %b %Y'),
        ]
        
        for pattern, date_format in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            if matches:
                logger.info(f"Found {len(matches)} transactions with generic pattern")
                
                for match in matches:
                    try:
                        trans_date = datetime.strptime(match[0].strip(), date_format).date()
                        description = match[1].strip()
                        amount_str = match[2].replace('R', '').replace('$', '').replace(',', '').strip()
                        amount = float(amount_str)
                        
                        # Skip if description is too short (likely parsing error)
                        if len(description) < 3:
                            continue
                        
                        transactions.append({
                            'date': trans_date,
                            'description': description,
                            'amount': abs(amount),
                            'type': 'debit' if amount < 0 else 'credit',
                            'reference': f"GEN-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                        })
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse generic transaction: {e}")
                        continue
                
                if transactions:
                    break
        
        return transactions
    
    def parse_html_email(self, html_content, bank_name):
        """Parse transaction table from HTML email"""
        from bs4 import BeautifulSoup
        
        transactions = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find transaction table
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip header row
                for row in rows[1:]:
                    cols = row.find_all('td')
                    
                    if len(cols) >= 3:
                        try:
                            # Assuming: Date | Description | Amount
                            date_text = cols[0].get_text().strip()
                            description = cols[1].get_text().strip()
                            amount_text = cols[2].get_text().strip()
                            
                            # Parse date (try multiple formats)
                            trans_date = None
                            for date_fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d %b %Y']:
                                try:
                                    trans_date = datetime.strptime(date_text, date_fmt).date()
                                    break
                                except ValueError:
                                    continue
                            
                            if not trans_date:
                                continue
                            
                            # Parse amount
                            amount_str = re.sub(r'[^\d\.\-]', '', amount_text)
                            amount = float(amount_str)
                            
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': abs(amount),
                                'type': 'debit' if amount < 0 else 'credit',
                                'reference': f"HTML-{trans_date.strftime('%Y%m%d')}"
                            })
                            
                        except (ValueError, IndexError):
                            continue
            
            logger.info(f"Extracted {len(transactions)} transactions from HTML email")
            
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
        
        return transactions
