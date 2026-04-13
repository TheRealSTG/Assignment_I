import streamlit as st
import logging
from io import BytesIO
from pathlib import Path
import base64
from personalizer import (
    fetch_landing_page, analyze_with_ai, personalize_html, 
    validate_html_output, ScrapingError, PersonalizationError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Ad-to-Page CRO Personalizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Styling
st.markdown("""
<style>
    .success-box { background-color: #d4edda; padding: 15px; border-radius: 5px; }
    .error-box { background-color: #f8d7da; padding: 15px; border-radius: 5px; }
    .comparison-container { display: flex; gap: 20px; }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🎯 Ad-to-Landing Page Personalizer")
st.markdown("Align your landing page perfectly with your ad creative to maximize conversions using AI-powered CRO.")

# Sidebar for Instructions & Configuration
with st.sidebar:
    st.header("📋 How It Works")
    st.markdown("""
    **Step 1:** Provide your ad creative (text or image)
    **Step 2:** Enter your landing page URL
    **Step 3:** Let AI analyze and personalize
    **Step 4:** View enhanced page with optimized CRO elements
    """)
    
    st.divider()
    st.header("⚙️ Configuration")
    
    if st.checkbox("Show API Setup"):
        st.info("""
        **Setup Required:**
        
        1. **OpenAI (Default):**
           - Set `OPENAI_API_KEY` environment variable
           - Or update `.env` file
        
        2. **Google Gemini:**
           - Set `AI_PROVIDER=gemini` in `.env`
           - Set `GEMINI_API_KEY` environment variable
        """)
    
    hallucination_mode = st.select_slider(
        "Hallucination Detection",
        options=["permissive", "moderate", "strict"],
        value="moderate"
    )

# Main content
st.markdown("---")

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("📢 Ad Creative Input")
    ad_text = st.text_area(
        "Input Ad Copy / Offer Details",
        height=150,
        placeholder="e.g., 'Get 30% off on premium features this week only. No credit card required.'"
    )
    
    ad_image = st.file_uploader(
        "Or Upload Ad Creative (Image)",
        type=["png", "jpg", "jpeg"],
        help="Image analysis coming soon"
    )
    
    if ad_image:
        st.image(ad_image, caption="Ad Creative Uploaded", use_column_width=True)
        ad_context = ad_text if ad_text else "Visual Ad (image provided)"
    else:
        ad_context = ad_text

with col2:
    st.subheader("🌐 Landing Page Input")
    landing_page_url = st.text_input(
        "Landing Page URL",
        placeholder="https://example.com/landing-page",
        help="Enter the complete URL of your landing page"
    )

st.markdown("---")

# Main execution button
if st.button("✨ Generate Personalized Page", type="primary", use_container_width=True):
    
    # Validation
    if not ad_context or not landing_page_url:
        st.error("❌ Please provide both ad creative and landing page URL")
        st.stop()
    
    # Processing
    with st.spinner("🔄 Processing... Fetching page & analyzing with AI..."):
        try:
            # Step 1: Fetch landing page
            logger.info(f"Fetching: {landing_page_url}")
            html_content, page_metadata = fetch_landing_page(landing_page_url)
            
            # Step 2: AI Analysis
            logger.info(f"Analyzing with AI: {ad_context[:50]}...")
            personalization = analyze_with_ai(ad_context, page_metadata)
            
            # Step 3: Apply personalization to HTML
            logger.info("Personalizing HTML...")
            personalized_html = personalize_html(html_content, personalization)
            
            # Step 4: Validate output
            is_valid, error_msg = validate_html_output(personalized_html)
            if not is_valid:
                st.warning(f"⚠️ HTML validation warning: {error_msg}")
        
        except ScrapingError as e:
            st.error(f"❌ Page Scraping Error: {str(e)}")
            st.markdown("""
            **Troubleshooting:**
            - Verify the URL is correct and publicly accessible
            - The site may block automated access (try a different URL)
            - Check your internet connection
            """)
            st.stop()
        
        except PersonalizationError as e:
            st.error(f"❌ AI Analysis Error: {str(e)}")
            st.markdown("""
            **Troubleshooting:**
            - Ensure API keys are configured correctly
            - Check your API quota/limits
            - Try again in a moment
            """)
            st.stop()
        
        except Exception as e:
            st.error(f"❌ Unexpected Error: {str(e)}")
            logger.exception("Unexpected error during personalization")
            st.stop()
    
    # Display Results
    st.success("✅ Analysis Complete! Here is your personalized CRO mapping:")
    
    st.subheader("📊 Element Modifications")
    
    comp_col1, comp_col2 = st.columns(2)
    
    with comp_col1:
        st.markdown("### 📄 Original Page Elements")
        st.info(f"**Page Title:** {page_metadata.get('original_title', 'N/A')}")
        st.info(f"**H1:** {page_metadata.get('original_h1', 'N/A')}")
        st.info(f"**Meta Description:** {page_metadata.get('original_meta_desc', 'N/A')[:80]}...")
        st.info(f"**CTA:** {page_metadata.get('cta_text', 'N/A')}")
    
    with comp_col2:
        st.markdown("### ✨ Personalized Page Elements")
        st.success(f"**Updated H1:** {personalization.get('h1', 'N/A')}")
        st.success(f"**Updated Description:** {personalization.get('meta_description', 'N/A')[:80]}...")
        st.success(f"**Updated Subheadline:** {personalization.get('subheadline', 'N/A')}")
        st.success(f"**Updated CTA:** {personalization.get('cta_text', 'N/A')}")
    
    st.divider()
    
    # AI Reasoning
    st.subheader("💡 Personalization Reasoning")
    st.info(personalization.get('reasoning', 'AI analysis complete'))
    
    st.divider()
    
    # Preview Section
    st.subheader("🔍 Live Preview")
    st.markdown("""
    *Below is a preview of how your enhanced landing page will look with the personalized elements:*
    """)
    
    # Create an interactive preview using HTML iframe
    preview_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .preview-container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; font-size: 2.5em; margin-bottom: 15px; }}
            .subheadline {{ font-size: 1.2em; color: #34495e; margin-bottom: 20px; }}
            .meta-info {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 0.9em; color: #7f8c8d; }}
            .cta-button {{ 
                background: #3498db; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                font-size: 1.1em;
                margin-top: 20px;
            }}
            .cta-button:hover {{ background: #2980b9; }}
            .original {{ opacity: 0.6; text-decoration: line-through; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="preview-container">
            <h1>{personalization.get('h1', 'Personalized Headline')}</h1>
            <p class="subheadline">{personalization.get('subheadline', 'Enhanced subheadline for conversion')}</p>
            <div class="meta-info">
                <strong>Page Description:</strong> {personalization.get('meta_description', 'Optimized meta description')}
            </div>
            <button class="cta-button">{personalization.get('cta_text', 'Call to Action')}</button>
        </div>
    </body>
    </html>
    """
    
    st.components.v1.html(preview_html, height=400)
    
    # Download Options
    st.divider()
    st.subheader("📥 Download Options")
    
    col_html, col_json = st.columns(2)
    
    with col_html:
        html_bytes = personalized_html.encode('utf-8')
        st.download_button(
            label="⬇️ Download Personalized HTML",
            data=html_bytes,
            file_name="personalized_landing_page.html",
            mime="text/html"
        )
    
    with col_json:
        json_str = str(personalization)
        st.download_button(
            label="⬇️ Download Changes (JSON)",
            data=json_str,
            file_name="personalization_changes.json",
            mime="application/json"
        )
    
    # Debug Information
    with st.expander("🔧 Debug Information"):
        st.write("**Page Metadata:**", page_metadata)
        st.write("**AI Personalization Output:**", personalization)