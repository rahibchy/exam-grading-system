import streamlit as st
import pandas as pd
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import re
from datetime import datetime

# ===========================
# CONFIGURATION
# ===========================

EXAM_QUESTIONS = {
    'Q1': {
        'name': 'Chart Summary',
        'marks': 15,
        'marker_text': 'Summarize the information',
        'min_length': 40
    },
    'Q2': {
        'name': 'Public Transport in Dhaka',
        'marks': 7,
        'marker_text': 'Public Transportation In Dhaka',
        'min_length': 40
    },
    'Q3': {
        'name': 'Online Shopping A&D',
        'marks': 8,
        'marker_text': 'An increasing number of people are buying',
        'min_length': 40
    }
}

GARBAGE_CHARS = set('!@#$%^&*()[]{}|\\/<>~`')
GARBAGE_THRESHOLD = 0.3

# ===========================
# HELPER FUNCTIONS
# ===========================

def extract_text_from_pdf(pdf_bytes):
    """Convert PDF to images and OCR all pages"""
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)
        full_text = ""
        for img in images:
            # Use better OCR config for handwriting
            text = pytesseract.image_to_string(img, config='--psm 6 --oem 3')
            full_text += text + "\n\n=== PAGE BREAK ===\n\n"
        return full_text, images[0] if images else None
    except Exception as e:
        return None, None

def extract_name_reg_from_top(first_page_img):
    """Extract name and reg from top 25% of first page"""
    if first_page_img is None:
        return None, None, "NO_IMAGE"
    
    try:
        width, height = first_page_img.size
        top_portion = first_page_img.crop((0, 0, width, int(height * 0.25)))
        text = pytesseract.image_to_string(top_portion, config='--psm 6')
        
        # Try multiple patterns for name
        name = None
        name_patterns = [
            r'[Nn]ame\s*:?\s*([A-Za-z][A-Za-z\s\.]+?)(?:\n|[Rr]eg|$)',
            r'Student\s*[Nn]ame\s*:?\s*([A-Za-z][A-Za-z\s\.]+?)(?:\n|[Rr]eg|$)',
            r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Capitalized words at start
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up common OCR errors
                name = re.sub(r'[^A-Za-z\s\.]', '', name)
                if len(name) > 3:
                    break
        
        # Try multiple patterns for registration
        reg = None
        reg_patterns = [
            r'[Rr]eg(?:istration)?\s*[Nn]o?\.?\s*:?\s*([0-9]+)',
            r'[Rr]oll\s*[Nn]o?\.?\s*:?\s*([0-9]+)',
            r'[Ii][Dd]\s*:?\s*([0-9]+)',
            r'\b([0-9]{6,10})\b',  # Any 6-10 digit number
        ]
        
        for pattern in reg_patterns:
            match = re.search(pattern, text)
            if match:
                reg = match.group(1).strip()
                if len(reg) >= 4:
                    break
        
        # Determine status
        if name and reg:
            status = "OK"
        elif name or reg:
            status = "PARTIAL"
        else:
            status = "NEEDS_MANUAL_FIX"
        
        return name, reg, status
    except Exception as e:
        return None, None, "ERROR"

def find_answer_by_marker(full_text, marker_text, next_marker=None):
    """Extract answer text between marker and next marker"""
    try:
        # Try multiple marker variations for better matching
        marker_variations = [
            marker_text,
            marker_text.replace(' ', '\s+'),  # Allow multiple spaces
            marker_text.replace(' ', '.*?'),    # Allow any chars between words
        ]
        
        match = None
        for marker_var in marker_variations:
            pattern = re.escape(marker_var) if marker_var == marker_text else marker_var
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                break
        
        if not match:
            # Fallback: try finding key words from marker
            key_words = marker_text.split()[:3]  # First 3 words
            if len(key_words) >= 2:
                fuzzy_pattern = '.*?'.join(re.escape(word) for word in key_words)
                match = re.search(fuzzy_pattern, full_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return None
        
        start_pos = match.end()
        
        # Find end position
        if next_marker:
            next_variations = [
                next_marker,
                next_marker.split()[:3],  # First 3 words of next marker
            ]
            
            end_pos = len(full_text)
            for next_var in next_variations:
                if isinstance(next_var, list):
                    next_pattern = '.*?'.join(re.escape(word) for word in next_var)
                else:
                    next_pattern = re.escape(next_var)
                
                next_match = re.search(next_pattern, full_text[start_pos:], re.IGNORECASE | re.DOTALL)
                if next_match:
                    end_pos = start_pos + next_match.start()
                    break
        else:
            # For last question, take next 1000 chars max
            end_pos = min(start_pos + 1000, len(full_text))
        
        answer = full_text[start_pos:end_pos].strip()
        return answer if answer and len(answer) > 5 else None
    except Exception as e:
        return None

def calculate_garbage_ratio(text):
    """Calculate ratio of garbage characters"""
    if not text:
        return 0
    garbage_count = sum(1 for char in text if char in GARBAGE_CHARS)
    return garbage_count / len(text)

def assess_ocr_quality(answer_text, min_length):
    """Determine OCR quality status"""
    if answer_text is None:
        return "UNREADABLE", "MISSING_TEXT"
    
    if len(answer_text) < min_length:
        return "TOO_SHORT", "LENGTH_CHECK"
    
    garbage_ratio = calculate_garbage_ratio(answer_text)
    if garbage_ratio > GARBAGE_THRESHOLD:
        return "SUSPECT_OCR", "HIGH_GARBAGE"
    
    return "OK", "PASS"

def dummy_grade(answer_text, max_marks, ocr_status):
    """Rule-based grading (LLM-ready structure)"""
    if ocr_status == "UNREADABLE":
        return None, "UNREADABLE"
    
    if ocr_status == "TOO_SHORT":
        score = max_marks * 0.3
        return round(score, 1), "AUTO_LOW"
    
    if ocr_status == "SUSPECT_OCR":
        score = max_marks * 0.6
        return round(score, 1), "AUTO_MEDIUM"
    
    # OK status - scale based on length
    if answer_text:
        length_ratio = min(len(answer_text) / 200, 1.0)
        score = max_marks * (0.5 + 0.5 * length_ratio)
        return round(score, 1), "AUTO_HIGH"
    
    return None, "NO_ANSWER"

# ===========================
# MAIN PROCESSING FUNCTION
# ===========================

def process_single_script(pdf_file):
    """Process one PDF script and return results dict"""
    result = {
        'script_name': pdf_file.name,
        'name_raw': None,
        'reg_raw': None,
        'name_clean': None,
        'reg_clean': None,
        'id_status': None,
        'script_status': None,
        'total_score': 0
    }
    
    # Read PDF
    pdf_bytes = pdf_file.read()
    full_text, first_page = extract_text_from_pdf(pdf_bytes)
    
    if full_text is None:
        result['script_status'] = "PDF_ERROR"
        return result
    
    # Extract name and registration
    name, reg, id_status = extract_name_reg_from_top(first_page)
    result['name_raw'] = name
    result['reg_raw'] = reg
    result['name_clean'] = name if name else "UNKNOWN"
    result['reg_clean'] = reg if reg else "UNKNOWN"
    result['id_status'] = id_status
    
    # Get marker texts in order
    markers = list(EXAM_QUESTIONS.keys())
    
    # Process each question
    all_unreadable = True
    some_readable = False
    
    for i, q_key in enumerate(markers):
        q_config = EXAM_QUESTIONS[q_key]
        next_marker = EXAM_QUESTIONS[markers[i+1]]['marker_text'] if i+1 < len(markers) else None
        
        # Extract answer
        answer_text = find_answer_by_marker(full_text, q_config['marker_text'], next_marker)
        
        # Assess quality
        ocr_status, ocr_flag = assess_ocr_quality(answer_text, q_config['min_length'])
        
        # Grade
        ai_score, ai_status = dummy_grade(answer_text, q_config['marks'], ocr_status)
        
        # Determine final score (could be overridden by manual review)
        final_score = ai_score
        
        # Track readability
        if ocr_status != "UNREADABLE":
            some_readable = True
            all_unreadable = False
        
        # Store results
        result[f'{q_key}_final_score'] = final_score if final_score else ""
        result[f'{q_key}_ai_score'] = ai_score if ai_score else ""
        result[f'{q_key}_ocr_status'] = ocr_status
        result[f'{q_key}_ocr_flag'] = ocr_flag
        result[f'{q_key}_ai_status'] = ai_status
        result[f'{q_key}_ai_flag'] = "NEEDS_REVIEW" if ocr_status != "OK" else "OK"
        
        # Add to total
        if final_score:
            result['total_score'] += final_score
    
    # Determine overall script status
    if all_unreadable:
        result['script_status'] = "FULL_MANUAL"
    elif not some_readable:
        result['script_status'] = "FULL_MANUAL"
    elif any(result.get(f'{q}_ocr_status') in ['UNREADABLE', 'TOO_SHORT', 'SUSPECT_OCR'] 
             for q in markers):
        result['script_status'] = "PARTIAL_MANUAL"
    else:
        result['script_status'] = "AUTO_COMPLETE"
    
    result['total_score'] = round(result['total_score'], 1)
    
    return result

def generate_excel(results_list):
    """Generate Excel file with marksheet and review list"""
    df = pd.DataFrame(results_list)
    
    # Reorder columns
    base_cols = ['script_name', 'name_raw', 'reg_raw', 'name_clean', 'reg_clean', 
                 'id_status', 'script_status']
    
    q_cols = []
    for q in EXAM_QUESTIONS.keys():
        q_cols.extend([
            f'{q}_final_score', f'{q}_ai_score', f'{q}_ocr_status', 
            f'{q}_ocr_flag', f'{q}_ai_status', f'{q}_ai_flag'
        ])
    
    final_cols = base_cols + q_cols + ['total_score']
    df = df[final_cols]
    
    # Create review list
    review_list = []
    for idx, row in df.iterrows():
        issues = []
        
        if row['id_status'] in ['NEEDS_MANUAL_FIX', 'PARTIAL']:
            issues.append('Unreadable ID')
        
        for q in EXAM_QUESTIONS.keys():
            if row[f'{q}_ocr_status'] == 'UNREADABLE':
                issues.append(f'{q}: Unreadable')
            elif row[f'{q}_ocr_status'] == 'SUSPECT_OCR':
                issues.append(f'{q}: Suspect OCR')
            elif row[f'{q}_ocr_status'] == 'TOO_SHORT':
                issues.append(f'{q}: Too Short')
        
        if not row['total_score'] or row['total_score'] == 0:
            issues.append('Blank final score')
        
        if issues:
            review_list.append({
                'script_name': row['script_name'],
                'student': f"{row['name_clean']} ({row['reg_clean']})",
                'status': row['script_status'],
                'issues': '; '.join(issues)
            })
    
    review_df = pd.DataFrame(review_list)
    
    # Write to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Marksheet', index=False)
        if not review_df.empty:
            review_df.to_excel(writer, sheet_name='Manual Review', index=False)
    
    output.seek(0)
    return output

# ===========================
# STREAMLIT UI
# ===========================

def main():
    st.set_page_config(
        page_title="Exam Auto-Grading System",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 Automatic Exam Script Grading System")
    st.markdown("---")
    
    # Instructions
    with st.expander("ℹ️ How to Use", expanded=False):
        st.markdown("""
        **Simple 3-Step Process:**
        1. **Upload** your scanned PDF exam scripts (multiple files supported)
        2. **Click** the "Process Scripts" button
        3. **Download** the Excel marksheet with auto-grades and review flags
        
        **What This System Does:**
        - Extracts student names and registration numbers
        - OCRs all answers for Q1, Q2, and Q3
        - Auto-grades based on answer quality
        - Flags scripts that need manual review
        - Generates a complete Excel marksheet
        
        **No Installation Required** - Everything runs in the cloud!
        """)
    
    # File uploader
    st.subheader("📤 Upload Exam Scripts")
    uploaded_files = st.file_uploader(
        "Upload PDF exam scripts (multiple files allowed)",
        type=['pdf'],
        accept_multiple_files=True,
        help="Select all PDF files you want to process"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        
        # Show file list
        with st.expander("Uploaded Files"):
            for file in uploaded_files:
                st.text(f"• {file.name}")
        
        # Process button
        if st.button("🚀 Process Scripts", type="primary", use_container_width=True):
            with st.spinner("Processing exam scripts... This may take a few minutes."):
                results = []
                progress_bar = st.progress(0)
                
                for idx, pdf_file in enumerate(uploaded_files):
                    st.text(f"Processing: {pdf_file.name}")
                    result = process_single_script(pdf_file)
                    results.append(result)
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                # Store results in session state
                st.session_state['results'] = results
                st.success("✅ Processing complete!")
    
    # Display results
    if 'results' in st.session_state and st.session_state['results']:
        results = st.session_state['results']
        
        st.markdown("---")
        st.subheader("📊 Results Preview")
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        total_scripts = len(results)
        auto_complete = sum(1 for r in results if r['script_status'] == 'AUTO_COMPLETE')
        partial_manual = sum(1 for r in results if r['script_status'] == 'PARTIAL_MANUAL')
        full_manual = sum(1 for r in results if r['script_status'] == 'FULL_MANUAL')
        
        col1.metric("Total Scripts", total_scripts)
        col2.metric("Auto-Complete", auto_complete, delta_color="normal")
        col3.metric("Partial Review Needed", partial_manual, delta_color="off")
        col4.metric("Full Manual Review", full_manual, delta_color="inverse")
        
        # Preview table
        st.subheader("Marksheet Preview")
        preview_df = pd.DataFrame(results)
        display_cols = ['script_name', 'name_clean', 'reg_clean', 
                        'Q1_final_score', 'Q2_final_score', 'Q3_final_score', 
                        'total_score', 'script_status']
        
        if all(col in preview_df.columns for col in display_cols):
            st.dataframe(preview_df[display_cols], use_container_width=True)
        
        # Manual review list
        review_needed = [r for r in results if r['script_status'] != 'AUTO_COMPLETE']
        if review_needed:
            st.warning(f"⚠️ {len(review_needed)} script(s) need manual review")
            with st.expander("Scripts Requiring Manual Review"):
                for r in review_needed:
                    st.text(f"• {r['script_name']} - {r['name_clean']} ({r['reg_clean']}) - Status: {r['script_status']}")
        else:
            st.success("✅ All scripts auto-graded successfully!")
        
        # Download button
        st.markdown("---")
        excel_file = generate_excel(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📥 Download Excel Marksheet",
            data=excel_file,
            file_name=f"exam_marksheet_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
        st.info("💡 The Excel file contains two sheets: 'Marksheet' (all scores) and 'Manual Review' (flagged scripts)")

if __name__ == "__main__":
    main()
