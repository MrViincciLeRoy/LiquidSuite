"""
PDF Parser - Extract transactions from bank statement PDFs
LiquidSuite/lsuite/gmail/parsers.py - COMPLETE FIXED VERSION
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
        
        # Log extracted text for debugging
        logger.info(f"Extracted text length: {len(text)} characters")
        logger.debug(f"First 500 chars: {text[:500]}")
        
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
        """Parse TymeBank PDF format - FIXED VERSION
        
        TymeBank format:
        Date Description Fees Money Out Money In Balance
        04 Sep 2025 EFT for CAPITEC S SEANEGO - - 250.00 250.05
        
        Multi-line format:
        10 Sep 2025 Purchase at Boxer Spr Mabopane
        525309988959
        - 512.46 - 417.59
        """
        transactions = []
        
        # Split text into lines for processing
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for lines starting with a date pattern
            date_match = re.match(r'^(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+)', line)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    rest_of_line = date_match.group(2).strip()
                    
                    # Parse the date
                    trans_date = datetime.strptime(date_str, '%d %b %Y').date()
                    
                    # Build description starting with rest of first line
                    description_parts = [rest_of_line]
                    
                    # Look ahead for continuation lines and amounts
                    j = i + 1
                    amounts_found = False
                    fees = money_out = money_in = balance = None
                    
                    # Check next few lines (max 5 lines ahead for multi-line transactions)
                    while j < len(lines) and j < i + 6:
                        next_line = lines[j].strip()
                        
                        # Stop if we hit another date (start of next transaction)
                        if re.match(r'^\d{1,2}\s+\w{3}\s+\d{4}', next_line):
                            break
                        
                        # ✅ FIX: Better pattern that validates amounts are actually monetary values
                        # Pattern: up to 4 amount fields (fees, money_out, money_in, balance)
                        # Each field is either "-" or a valid decimal number
                        amount_pattern = r'^(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s*$'
                        amount_match = re.match(amount_pattern, next_line)
                        
                        if amount_match:
                            # Found the amounts line
                            fees = amount_match.group(1).strip()
                            money_out = amount_match.group(2).strip()
                            money_in = amount_match.group(3).strip()
                            balance = amount_match.group(4).strip()
                            amounts_found = True
                            i = j  # Move main counter to this position
                            break
                        else:
                            # Check if amounts are at the end of this line
                            inline_pattern = r'(.+?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s*$'
                            inline_amount_match = re.search(inline_pattern, next_line)
                            
                            if inline_amount_match:
                                # Description continues and amounts are on same line
                                description_parts.append(inline_amount_match.group(1).strip())
                                fees = inline_amount_match.group(2).strip()
                                money_out = inline_amount_match.group(3).strip()
                                money_in = inline_amount_match.group(4).strip()
                                balance = inline_amount_match.group(5).strip()
                                amounts_found = True
                                i = j
                                break
                            else:
                                # ✅ FIX: Only add to description if it's not a random number
                                # Skip lines that are just long numbers (like card numbers: 525309988959)
                                if next_line and not re.match(r'^\d{10,}$', next_line):
                                    # Check if it's a valid description line
                                    if len(next_line) > 0 and not next_line.startswith('-'):
                                        description_parts.append(next_line)
                        
                        j += 1
                    
                    # Try to find amounts on the same line as date if not found yet
                    if not amounts_found:
                        same_line_pattern = r'(.+?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s*$'
                        same_line_match = re.search(same_line_pattern, rest_of_line)
                        
                        if same_line_match:
                            description_parts = [same_line_match.group(1).strip()]
                            fees = same_line_match.group(2).strip()
                            money_out = same_line_match.group(3).strip()
                            money_in = same_line_match.group(4).strip()
                            balance = same_line_match.group(5).strip()
                            amounts_found = True
                    
                    # Process the transaction if amounts were found
                    if amounts_found:
                        # Build full description
                        description = ' '.join(description_parts)
                        description = ' '.join(description.split())  # Clean whitespace
                        
                        # Skip if description is too short or looks like a header
                        if len(description) < 3 or 'Description' in description or 'Money Out' in description:
                            i += 1
                            continue
                        
                        # ✅ FIX: Parse amounts with validation
                        def parse_amount_safe(amount_str):
                            """Safely parse amount with validation"""
                            if not amount_str or amount_str == '-':
                                return 0
                            try:
                                # Remove commas and spaces
                                cleaned = amount_str.replace(',', '').replace(' ', '').strip()
                                # Ensure it's not too large (max 10 million for a single transaction)
                                val = float(cleaned)
                                if val > 10_000_000:  # 10 million limit
                                    logger.warning(f"Amount too large, likely parsing error: {val} from '{amount_str}'")
                                    return 0
                                return val
                            except (ValueError, AttributeError):
                                logger.warning(f"Could not parse amount: '{amount_str}'")
                                return 0
                        
                        # Determine transaction type and amount
                        amount = 0
                        trans_type = 'debit'
                        
                        # Check Money In first (credits)
                        money_in_val = parse_amount_safe(money_in)
                        if money_in_val > 0:
                            amount = money_in_val
                            trans_type = 'credit'
                        
                        # Then check Money Out (debits)
                        money_out_val = parse_amount_safe(money_out)
                        if amount == 0 and money_out_val > 0:
                            amount = money_out_val
                            trans_type = 'debit'
                        
                        # Then check Fees (also debits)
                        fees_val = parse_amount_safe(fees)
                        if amount == 0 and fees_val > 0:
                            amount = fees_val
                            trans_type = 'debit'
                            description = f"{description} (Fee)"
                        
                        # Only add if we have a valid amount
                        if amount > 0:
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': amount,
                                'type': trans_type,
                                'reference': f"TYME-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                            })
                            logger.debug(f"Parsed transaction: {description[:30]} = {amount}")
                        else:
                            logger.debug(f"Skipped transaction with zero amount: {description[:30]}")
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse TymeBank transaction: {e}")
            
            i += 1
        
        if not transactions:
            logger.warning("No transactions found with TymeBank pattern")
            logger.debug(f"Text sample for debugging:\n{text[:1000]}")
        else:
            logger.info(f"Successfully parsed {len(transactions)} TymeBank transactions")
        
        return transactions
    
    def _parse_capitec(self, text):
        """Parse Capitec PDF format"""
        transactions = []
        
        # Capitec typically uses format: Date Description Amount
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for date patterns at start of line
            date_patterns = [
                (r'^(\d{4}/\d{2}/\d{2})\s+(.+)', '%Y/%m/%d'),
                (r'^(\d{2}/\d{2}/\d{4})\s+(.+)', '%d/%m/%Y'),
                (r'^(\d{2}\s+\w{3})\s+(.+)', '%d %b'),
            ]
            
            matched = False
            for pattern, date_format in date_patterns:
                date_match = re.match(pattern, line)
                
                if date_match:
                    try:
                        date_str = date_match.group(1).strip()
                        rest = date_match.group(2).strip()
                        
                        # Handle dates without year
                        if date_format == '%d %b':
                            current_year = datetime.now().year
                            date_str = f"{date_str} {current_year}"
                            date_format = '%d %b %Y'
                        
                        trans_date = datetime.strptime(date_str, date_format).date()
                        
                        # Try to find amount on same line
                        amount_pattern = r'(.+?)\s+(-?R?\s?[\d\s,]+\.\d{2})\s*$'
                        amount_match = re.search(amount_pattern, rest)
                        
                        if amount_match:
                            description = amount_match.group(1).strip()
                            amount_str = amount_match.group(2).replace('R', '').replace(',', '').replace(' ', '').strip()
                            
                            try:
                                amount = float(amount_str)
                                
                                if len(description) >= 3:
                                    transactions.append({
                                        'date': trans_date,
                                        'description': description,
                                        'amount': abs(amount),
                                        'type': 'debit' if amount < 0 or '-' in amount_match.group(2) else 'credit',
                                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                                    })
                                    matched = True
                            except ValueError:
                                pass
                        
                        if matched:
                            break
                    
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse Capitec transaction: {e}")
            
            i += 1
        
        if not transactions:
            logger.warning("No transactions found with Capitec pattern")
        else:
            logger.info(f"Successfully parsed {len(transactions)} Capitec transactions")
        
        return transactions
    
    def _parse_generic(self, text):
        """Generic PDF parsing for unknown banks"""
        transactions = []
        
        # Generic patterns that might work for various banks
        patterns = [
            (r'(\d{2}/\d{2}/\d{4})\s*[|\|]\s*([^|\|]+?)\s*[|\|]\s*(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            (r'(\d{2}/\d{2}/\d{4})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            (r'(\d{4}-\d{2}-\d{2})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%Y-%m-%d'),
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
                        
                        # Skip if description is too short
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
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip header row
                for row in rows[1:]:
                    cols = row.find_all('td')
                    
                    if len(cols) >= 3:
                        try:
                            date_text = cols[0].get_text().strip()
                            description = cols[1].get_text().strip()
                            amount_text = cols[2].get_text().strip()
                            
                            # Parse date
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
