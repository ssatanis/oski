# PromptGen - OSCE Rubric Converter

> **Transforming medical education assessments with intelligent design and user-centric experience**

A completely redesigned web application that transforms OSCE exam rubrics into AI-ready prompts with an intuitive, medical professional-friendly interface following Oski's design language.

## ✨ What's New in This Version

### 🎨 Complete UI/UX Overhaul
- **Oski Design Language Integration**: Seamlessly matches Oski's professional aesthetic with Geist and Prata fonts
- **Medical Professional Focused**: Removed technical jargon, uses intuitive language for healthcare educators
- **Modern Visual Design**: Clean cards, subtle gradients, rounded corners, and professional animations
- **Responsive Layout**: Optimized for desktop and tablet use in medical education environments

### 🚀 Enhanced User Experience
- **Intuitive Two-Stage Workflow**: 
  1. **Upload Stage**: Prominent, centered file upload with clear instructions
  2. **Dashboard Stage**: Interactive rubric editing with real-time preview
- **Drag & Drop Excellence**: Enhanced file upload with visual feedback and hover animations
- **Smart Processing Feedback**: Clean progress indicators with meaningful status messages
- **Seamless Transitions**: Smooth animations between stages using Framer Motion

### 📊 Interactive Rubric Dashboard
- **Visual Section Breakdown**: Rubrics organized by assessment sections (Patient History, Physical Exam, etc.)
- **In-line Editing**: Direct editing of descriptions, points, and criteria
- **Real-time Updates**: Changes immediately reflected in the underlying data structure
- **Assessment Summary**: Quick overview of total sections, items, and points
- **Live Code Preview**: Optional technical view for advanced users

### 📥 Enhanced Export Options
- **Dual Format Support**: Export as both YAML and JSON files
- **Professional Labeling**: Clear "Download YAML File" and "Download JSON File" buttons
- **Smart Naming**: Files automatically named based on original document
- **Visual Export Interface**: Prominent export options in dedicated cards

### 🔧 Technical Improvements
- **TypeScript Interface Definitions**: Comprehensive type safety for rubric data structures
- **Optimized State Management**: Efficient handling of large rubric datasets
- **Error Handling**: User-friendly error messages without technical details
- **Performance**: Optimized animations and reduced bundle size

## 🎯 Key Features for Medical Professionals

### User-Friendly Language
- "Upload your OSCE Rubric" instead of technical file processing terms
- "Assessment Sections" instead of "YAML sections"
- "Export Options" instead of "Download formats"
- Clear progress messages like "Processing Rubric..." instead of technical status codes

### Intuitive Interface Elements
- **Visual Status Indicators**: Color-coded progress with meaningful icons
- **Section-Based Organization**: Rubric items grouped by medical assessment areas
- **Point-Based Editing**: Simple numerical inputs for scoring criteria
- **Criteria Descriptions**: Text areas for detailed assessment guidelines

### Professional Aesthetics
- **Medical Education Appropriate**: Clean, academic appearance suitable for institutional use
- **Accessibility Focused**: High contrast, readable fonts, and clear visual hierarchy
- **Print-Friendly**: Layouts that translate well to printed documentation
- **Consistent Branding**: Matches Oski's established visual identity

## 🛠️ Architecture & Implementation

### Frontend Stack
```typescript
- Next.js 15 (App Router)
- TypeScript for type safety
- Tailwind CSS with custom Oski design system
- Framer Motion for animations
- Monaco Editor for code editing
- React Dropzone for file uploads
- Lucide React for icons
```

### Design System Classes
```css
.oski-heading     // Prata font for headings
.oski-card        // Consistent card styling with hover effects
.oski-button-primary     // Black buttons with hover animations
.oski-button-secondary   // Outlined buttons with fill on hover
.oski-upload-area        // Enhanced drag-and-drop styling
```

### Key Components
- **Upload Interface**: Centered, prominent file upload with visual feedback
- **Processing Status**: Clean progress indicators with meaningful messages
- **Rubric Editor**: Interactive forms for editing assessment criteria
- **Export Dashboard**: Professional export options with clear labeling
- **Code Preview**: Optional technical view with syntax highlighting

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.8+
- Azure OpenAI API access

### Installation
```bash
# Frontend setup
cd frontend
npm install
npm run dev

# Backend setup (in separate terminal)
cd ../backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Configuration
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend (.env)
AZURE_OPENAI_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

## 📖 Usage Guide

### 1. Upload Your Rubric
- Navigate to http://localhost:3000
- Drag and drop your OSCE rubric file or click to browse
- Supported formats: PDF, Word, Excel, text files, images
- Click "Process Rubric" to begin conversion

### 2. Review and Edit
- Automatic transition to interactive dashboard
- Edit section descriptions, point values, and assessment criteria
- Real-time updates to the underlying data structure
- View summary statistics in the sidebar

### 3. Export Your Results
- Choose between YAML or JSON format
- Files automatically named based on original document
- Download immediately or save changes first
- Use exported files in your AI assessment systems

## 🎨 Design Philosophy

### Medical Professional Focus
- **Clarity Over Complexity**: Simple, clear interfaces over technical complexity
- **Professional Appearance**: Suitable for academic and institutional environments
- **Intuitive Workflows**: Natural progression from upload to editing to export
- **Meaningful Feedback**: Status messages that make sense to educators

### Oski Design Integration
- **Typography**: Prata for headings (professional, academic), Geist for body text
- **Color Palette**: Professional blacks, grays, and whites with subtle accent colors
- **Spacing**: Generous whitespace for clarity and focus
- **Interactions**: Subtle hover effects and smooth transitions

### Accessibility & Usability
- **High Contrast**: Ensures readability in various lighting conditions
- **Clear Hierarchy**: Visual organization that guides user attention
- **Responsive Design**: Works well on desktop monitors and tablets
- **Error Prevention**: Clear validation and helpful error messages

## 🔧 Customization

### Extending the Design System
```css
/* Custom Oski utilities in globals.css */
.oski-card { /* Base card styling */ }
.oski-button-primary { /* Primary button styling */ }
.oski-upload-area { /* Upload area styling */ }
```

### Adding New Export Formats
```typescript
// Extend the downloadFile function in page.tsx
const downloadFile = async (format: 'yaml' | 'json' | 'csv') => {
  // Add new format handling
}
```

### Custom Assessment Sections
```typescript
// Modify RubricSection interface in page.tsx
interface RubricSection {
  section_name: string;
  section_id: string;
  description: string;
  items: RubricItem[];
  // Add custom fields here
}
```

## 🌟 Success Metrics

### User Experience Improvements
- **Reduced Clicks**: Single-page workflow reduces navigation complexity
- **Faster Processing**: Visual feedback keeps users engaged during processing
- **Clearer Outcomes**: Immediate preview of results with easy editing
- **Professional Appearance**: Interface suitable for institutional presentations

### Technical Achievements
- **100% Type Safety**: Full TypeScript implementation
- **Responsive Design**: Optimized for various screen sizes
- **Performance**: Smooth animations and fast interactions
- **Maintainability**: Clean, documented code following React best practices

## 📞 Support & Feedback

For questions about the medical education workflow or technical implementation, please refer to the main Oski documentation or contact the development team.

---

*This application is part of the Oski ecosystem for transforming medical education through intelligent assessment tools.*
