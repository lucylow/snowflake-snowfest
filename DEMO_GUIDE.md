# SNOW STREAMLINE - Demo Guide

## 🎬 Quick Demo Setup

This guide will help you prepare a compelling 3-5 minute demo video for the Snow Fest Hackathon submission.

---

## 📋 Pre-Demo Checklist

### 1. Environment Setup
- [ ] Backend server running (`python backend/main.py` or Docker)
- [ ] Frontend running (`npm run dev`)
- [ ] Phantom wallet installed and connected to devnet
- [ ] Test SOL in wallet (request airdrop if needed)
- [ ] Sample protein sequence and ligand files ready

### 2. Test Data Preparation

#### Sample Protein Sequence (for AlphaFold prediction):
```
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL
```

#### Sample Ligand Files:
- Download from PubChem (e.g., Aspirin: CID 2244)
- Or use provided test files in `/test_data/` directory

### 3. Browser Setup
- [ ] Clear browser cache
- [ ] Use incognito/private mode for clean demo
- [ ] Full-screen browser window (F11)
- [ ] Zoom set to 100%
- [ ] Screen recording software ready (OBS, Loom, etc.)

---

## 🎥 Demo Script (3-5 minutes)

### **Part 1: Introduction (30 seconds)**

**What to Say:**
> "Hi! I'm [Your Name], and I'm excited to present SNOW STREAMLINE - an AI-powered drug discovery platform that combines AlphaFold protein structure prediction, molecular docking, and blockchain verification. Today I'll show you how we're revolutionizing drug discovery by making advanced tools accessible to everyone."

**What to Show:**
- Landing page with hero section
- Smooth scroll through features

---

### **Part 2: Core Workflow (2-3 minutes)**

#### **Step 1: Submit a Docking Job (30 seconds)**

**What to Say:**
> "Let's start by submitting a drug discovery job. I'll use a protein sequence - this could be a target for cancer therapy or any disease."

**What to Show:**
1. Navigate to Dashboard
2. Click "Submit New Job"
3. Paste protein sequence OR upload PDB file
4. Upload ligand file (SDF/MOL2)
5. Configure docking parameters (optional)
6. Click "Submit Job"
7. Show job created with status "PREDICTING_STRUCTURE"

**Key Points to Highlight:**
- ✅ Easy-to-use interface
- ✅ Supports both sequences and PDB files
- ✅ Real-time status updates

---

#### **Step 2: AlphaFold Structure Prediction (30 seconds)**

**What to Say:**
> "Our platform automatically uses AlphaFold to predict the 3D structure of the protein. This typically takes a few minutes, but I'll show you a completed prediction."

**What to Show:**
1. Navigate to job details page
2. Show AlphaFold prediction results
3. Display pLDDT quality score
4. Show 3D structure visualization
5. Highlight quality metrics

**Key Points to Highlight:**
- ✅ Automated AlphaFold integration
- ✅ Quality scoring (pLDDT)
- ✅ No manual intervention needed

---

#### **Step 3: Molecular Docking Results (30 seconds)**

**What to Say:**
> "Once we have the structure, our platform automatically runs molecular docking to find the best binding poses. Here are the results ranked by binding affinity."

**What to Show:**
1. Show docking results table
2. Display binding affinity scores
3. Show multiple binding poses
4. Click on a pose to view in 3D
5. Rotate and zoom the 3D structure
6. Highlight protein-ligand interactions

**Key Points to Highlight:**
- ✅ Automated docking pipeline
- ✅ Multiple binding poses
- ✅ Interactive 3D visualization
- ✅ Binding affinity scoring

---

#### **Step 4: AI Analysis & Report Generation (45 seconds)**

**What to Say:**
> "Now comes the AI magic. Our platform uses GPT-4 to generate comprehensive analysis reports tailored to different stakeholders. Let me generate a report for a researcher."

**What to Show:**
1. Navigate to AI Analysis section
2. Select analysis type (Binding Affinity)
3. Choose stakeholder (Researcher)
4. Click "Generate Analysis"
5. Show AI report loading
6. Display comprehensive report with:
   - Binding analysis
   - Drug-likeness scores
   - ADMET properties
   - Toxicity predictions
7. Switch to "Investor" stakeholder view
8. Show different report format (business-focused)

**Key Points to Highlight:**
- ✅ AI-powered analysis
- ✅ Stakeholder-specific reports
- ✅ Comprehensive property predictions
- ✅ Multiple report formats

---

#### **Step 5: Blockchain Storage & Verification (45 seconds)**

**What to Say:**
> "Finally, let's store this report on the Solana blockchain to ensure its integrity and create an immutable audit trail. This is crucial for regulatory compliance and research verification."

**What to Show:**
1. Click "Store on Blockchain" button
2. Show Phantom wallet connection (if not already connected)
3. Show transaction approval dialog
4. Approve transaction
5. Display transaction signature
6. Show Solana Explorer link
7. Navigate to Blockchain page
8. Enter transaction signature
9. Show verified report data
10. Click Solana Explorer link to show on-chain data

**Key Points to Highlight:**
- ✅ Immutable storage
- ✅ Low transaction cost (~$0.0001)
- ✅ Public verification
- ✅ Regulatory compliance

---

### **Part 3: Innovation Highlights (1 minute)**

**What to Say:**
> "What makes SNOW STREAMLINE unique is our end-to-end integration of cutting-edge technologies. We're the first platform to combine AlphaFold structure prediction, automated molecular docking, AI-powered analysis, and blockchain verification in a single, user-friendly interface. This democratizes access to tools that typically cost millions of dollars and require specialized expertise."

**What to Show:**
- Architecture diagram (if available)
- Key features slide
- Use cases:
  - Academic research
  - Pharmaceutical companies
  - Biotech startups
  - Public health

**Key Points to Highlight:**
- ✅ First-of-its-kind integration
- ✅ Democratized access
- ✅ Cost-effective solution
- ✅ Real-world impact

---

### **Part 4: Impact & Future (30 seconds)**

**What to Say:**
> "SNOW STREAMLINE has the potential to accelerate drug discovery from years to months, reduce costs by 90%, and enable researchers worldwide to access enterprise-grade tools. We're excited about the future and plan to add features like collaborative research, NFT milestones, and mobile applications. Thank you for watching!"

**What to Show:**
- Impact statistics
- Future roadmap
- Call-to-action

---

## 🎬 Recording Tips

### Technical Setup
1. **Resolution**: Record in 1080p minimum (1920x1080)
2. **Frame Rate**: 30 FPS minimum
3. **Audio**: Use a good microphone, minimize background noise
4. **Screen Recording**: 
   - OBS Studio (free, professional)
   - Loom (easy, cloud-based)
   - QuickTime (Mac)
   - Windows Game Bar (Windows)

### Best Practices
1. **Practice First**: Run through the demo 2-3 times before recording
2. **Clear Narration**: Speak clearly and at a moderate pace
3. **Smooth Navigation**: Avoid rapid mouse movements
4. **Highlight Key Features**: Use cursor movements to guide attention
5. **Show, Don't Tell**: Let the interface speak for itself
6. **Keep It Concise**: Stay within 3-5 minutes
7. **Edit if Needed**: Trim pauses, add captions if helpful

### Common Mistakes to Avoid
- ❌ Rushing through features
- ❌ Showing errors or bugs (use pre-tested data)
- ❌ Unclear audio
- ❌ Too much text on screen
- ❌ Going over time limit
- ❌ Not highlighting innovation

---

## 📊 Demo Metrics to Highlight

During the demo, mention these key metrics:

- **Time Savings**: "What used to take weeks now takes minutes"
- **Cost Reduction**: "90% reduction in infrastructure costs"
- **Accuracy**: "AlphaFold provides atomic-level accuracy"
- **Transaction Cost**: "Blockchain storage costs less than $0.0001"
- **Accessibility**: "Available to researchers worldwide"

---

## 🎯 Alternative Demo Scenarios

### Scenario A: Academic Researcher
Focus on:
- Research reproducibility
- Peer-review ready reports
- Citation-ready data
- Blockchain verification for publications

### Scenario B: Biotech Startup
Focus on:
- Investor-ready reports
- Cost savings
- Time-to-market acceleration
- Regulatory compliance

### Scenario C: Pharmaceutical Company
Focus on:
- Batch processing capabilities
- Integration with existing workflows
- Regulatory documentation
- Audit trails

---

## 📝 Post-Demo Checklist

After recording:
- [ ] Review video for clarity
- [ ] Trim unnecessary pauses
- [ ] Add captions/subtitles (optional but recommended)
- [ ] Export in MP4 format (H.264 codec)
- [ ] Upload to YouTube (unlisted) or Vimeo
- [ ] Add video link to Devpost submission
- [ ] Create thumbnail image
- [ ] Write video description

---

## 🚀 Quick Start Commands

```bash
# Terminal 1: Start Backend
cd backend
python main.py

# Terminal 2: Start Frontend
npm run dev

# Terminal 3: Request Test SOL (if needed)
# Use the airdrop feature in the app or:
solana airdrop 1 YOUR_WALLET_ADDRESS --url devnet
```

---

## 📞 Troubleshooting

### Backend Not Starting
- Check Python version (3.9+)
- Install dependencies: `pip install -r backend/requirements.txt`
- Check database connection
- Verify environment variables

### Frontend Not Loading
- Check Node.js version (18+)
- Install dependencies: `npm install`
- Check API URL in `.env.local`
- Clear browser cache

### Wallet Connection Issues
- Ensure Phantom wallet is installed
- Switch to devnet in Phantom settings
- Request airdrop for test SOL
- Check Solana RPC URL

### Docking Jobs Failing
- Verify AutoDock Vina is installed
- Check file formats (PDB, SDF, MOL2)
- Review backend logs for errors
- Ensure sufficient disk space

---

**Good luck with your demo! 🎉**
