# 📝 Automatic Exam Script Grading System

**Zero-effort, fully hosted exam grading system** for handwritten answer scripts.

## 🎯 What This Does

- Upload scanned PDF exam scripts
- Automatically extract student names and registration numbers
- OCR all answers for Q1, Q2, and Q3
- Auto-grade based on answer quality
- Flag scripts needing manual review
- Download complete Excel marksheet

## 🚀 Deployment Steps (5 Minutes)

### Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it something like `exam-grading-system`
3. Make it **Public** (required for Streamlit Cloud free tier)

### Step 2: Upload Files

Upload these 4 files to your repository:

```
exam-grading-system/
├── app.py
├── requirements.txt
├── packages.txt
└── README.md
```

**Method 1: Via GitHub Web Interface**
- Click "Add file" → "Upload files"
- Drag and drop all 4 files
- Click "Commit changes"

**Method 2: Via Git Command Line**
```bash
git clone https://github.com/YOUR_USERNAME/exam-grading-system.git
cd exam-grading-system
# Copy the 4 files into this folder
git add .
git commit -m "Initial commit"
git push
```

### Step 3: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub account (if not already connected)
4. Select:
   - **Repository:** YOUR_USERNAME/exam-grading-system
   - **Branch:** main
   - **Main file path:** app.py
5. Click "Deploy"

### Step 4: Wait for Deployment

- Deployment takes 3-5 minutes
- You'll see build logs
- Once complete, you'll get a permanent URL like:
  `https://YOUR-APP-NAME.streamlit.app`

### Step 5: Start Using

1. Open your app URL
2. Upload PDF scripts
3. Click "Process Scripts"
4. Download Excel marksheet

**That's it! No installation, no command line, no setup.**

---

## 📋 Exam Format (Pre-configured)

The system expects this exact format:

**Q1 - Chart Summary (15 marks)**
- Marker: "Summarize the information"

**Q2 - Public Transport in Dhaka (7 marks)**
- Marker: "Public Transportation In Dhaka"

**Q3 - Online Shopping A&D (8 marks)**
- Marker: "An increasing number of people are buying"

---

## 📊 Output Excel Structure

### Sheet 1: Marksheet
Columns for each script:
- Basic Info: script_name, name, registration, ID status
- Q1: final_score, ai_score, ocr_status, flags
- Q2: final_score, ai_score, ocr_status, flags
- Q3: final_score, ai_score, ocr_status, flags
- Total Score

### Sheet 2: Manual Review
List of scripts needing attention:
- Script name
- Student details
- Status (PARTIAL_MANUAL / FULL_MANUAL)
- Specific issues

---

## 🔧 Troubleshooting

### "ModuleNotFoundError" during deployment
- Make sure `requirements.txt` and `packages.txt` are in the root directory
- Wait for full deployment to complete (3-5 min)

### "OCR not working"
- Streamlit Cloud has Tesseract pre-installed via `packages.txt`
- No additional setup needed

### "App is slow"
- OCR processing takes time (1-2 min per script)
- This is normal for cloud processing

### "Can't upload files"
- Make sure files are PDFs (not images or other formats)
- File size limit: 200MB per file on Streamlit Cloud

---

## 🔄 Future Upgrades

The code is structured to easily upgrade to LLM-based grading:

1. Replace `dummy_grade()` function
2. Add API key configuration in Streamlit secrets
3. Call Claude/GPT API for semantic grading
4. Keep all other logic intact

---

## 📞 Support

If the app stops working:
1. Check Streamlit Cloud dashboard for errors
2. View app logs in Streamlit Cloud
3. Redeploy if needed (click "Reboot app")

---

## ✅ Confirmation Checklist

Before deploying, confirm you have:

- [ ] Created GitHub repository (public)
- [ ] Uploaded all 4 files (app.py, requirements.txt, packages.txt, README.md)
- [ ] Files are in repository root (not in a subfolder)
- [ ] Connected Streamlit Cloud to GitHub
- [ ] Selected correct repository and app.py
- [ ] Waited for deployment to complete

**Once deployed, bookmark your app URL and share it with colleagues!**
