from typing import Dict, Any
import json
import re
from anthropic import AsyncAnthropic
import os
from dotenv import load_dotenv

load_dotenv()

class LLMCloner:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.max_tokens = 15000
        
    async def generate_complete_clone(self, design_context: Dict[str, Any]) -> str:
        """Generate complete website clone with continuation handling"""
        
        # try single-pass generation first
        complete_html = await self._generate_single_pass(design_context)
        
        # Check if code is complete, if not use continuation
        if not self._is_html_complete(complete_html):
            print("Initial generation incomplete, using continuation approach...")
            complete_html = await self._generate_with_continuation(design_context)
        
        # Final validation and cleanup
        complete_html = self._ensure_html_completeness(complete_html)

        print(f"Complete HTML: {complete_html}")
        
        return complete_html
    
    async def _generate_single_pass(self, design_context: Dict[str, Any]) -> str:
        """Attempt single-pass generation with optimized prompt"""
        
        prompt = self._prepare_optimized_prompt(design_context)
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=self.max_tokens,
            temperature=0.2,
            system="""You are an expert web developer. Generate a complete HTML and CSS implementation that clones the original website's layout, colors, fonts, text sizes, porportions, images, svg icons, and styles. Focus on all of these along with visual accuracy and responsive design. Don't leave any components out.""",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._clean_html(response.content[0].text)
    
    async def _generate_with_continuation(self, design_context: Dict[str, Any]) -> str:
        """Generate complete HTML using continuation approach"""
        
        html_parts = []
        iteration = 0
        max_iterations = 4
        
        while iteration < max_iterations:
            if iteration == 0:
                prompt = self._prepare_initial_prompt(design_context)
                system_msg = "Generate the beginning of a complete HTML document. Start with DOCTYPE, head section, and begin the body. If truncated, I will ask you to continue."
            else:
                current_html = ''.join(html_parts)
                prompt = self._prepare_continuation_prompt(current_html, design_context)
                system_msg = "Continue the HTML exactly where it left off. Complete cloning any unfinished elements and continue with the remaining structure."
            
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=self.max_tokens,
                temperature=0.2,
                system=system_msg,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            clean_html = self._clean_html(response_text)
            
            # Check if this completes the HTML
            if iteration == 0:
                html_parts.append(clean_html)
                if self._is_html_complete(clean_html):
                    break
            else:
                # For continuations, merge intelligently
                merged_html = self._merge_continuation(html_parts[0], clean_html)
                html_parts = [merged_html]
                if self._is_html_complete(merged_html):
                    break
            
            iteration += 1
            print(f"Continuation iteration {iteration} completed")
        
        return html_parts[0] if html_parts else ""
    
    def _prepare_optimized_prompt(self, design_context: Dict[str, Any]) -> str:
        """Prepare optimized prompt for single-pass generation"""
        
        # Truncate large data to fit within token limits
        computed_styles = design_context.get('computed_styles', {})
        styles = design_context.get('styles', [])
        computed_styles = design_context.get('computed_styles', {})
        images = design_context.get('images', [])

        print(f"Styles: {styles}")
        
        # Create a structured prompt
        prompt = f"""Clone this website:

HTML Structure:
{design_context.get('html', '')}

Styles:
{json.dumps(computed_styles, indent=2)}

Images:
{json.dumps(images, indent=2)}

Additional Styles:
{json.dumps(styles, indent=2)}

Please generate a complete HTML and CSS implementation that clones the original design. Focus on:
- Maintaining the visual hierarchy
- Preserving the styling and layout (colors, fonts, text sizes, porportions, images, svg icons, and styles)
- Ensuring responsive design
- Optimizing for performance
- Following web development best practices

Return the complete HTML and CSS code that can be used to recreate the website with all of its components. I should be able to copy and paste the code into an iframe and see the website. You should only return the code, no other text."""
        
        return prompt
    
    def _prepare_initial_prompt(self, design_context: Dict[str, Any]) -> str:
        """Prepare prompt for initial generation in continuation mode"""
        computed_styles = design_context.get('computed_styles', {})
        styles = design_context.get('styles', [])
        computed_styles = design_context.get('computed_styles', {})
        images = design_context.get('images', [])
        
        return f"""Clone this website:

HTML Structure:
{design_context.get('html', '')}

Styles:
{json.dumps(computed_styles, indent=2)}

Images:
{json.dumps(images, indent=2)}

Additional Styles:
{json.dumps(styles, indent=2)}

Please generate a complete HTML and CSS implementation that closely matches the original design. Focus on:
- Maintaining the visual hierarchy
- Preserving the styling and layout (colors, fonts, text sizes, porportions, images, svg icons, and styles)
- Ensuring responsive design
- Optimizing for performance
- Following web development best practices

Begin the HTML and CSS code that can be used to recreate the website with all of its components. I should be able to copy and paste the code into an iframe and see the website. You should only return the code, no other text. If you get cut off, I'll ask you to continue:"""
    
    def _prepare_continuation_prompt(self, current_html: str, design_context: Dict[str, Any]) -> str:
        """Prepare continuation prompt"""
        
        # Get last 800 characters for context
        context = current_html[-800:] if len(current_html) > 800 else current_html
        
        return f"""Continue the HTML exactly where it left off:

CURRENT HTML (ending):
...{context}

Continue from exactly where it ended. Complete cloning any unfinished elements, ensuring the layout, color, text styles, images, svg icons and styles match the website. Continue cloning with the remaining HTML structure until the document is complete with </html>.

Continue the code:"""
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML from LLM response"""
        # Remove markdown code blocks
        html = re.sub(r'```html\s*\n?', '', html, flags=re.IGNORECASE)
        html = re.sub(r'```\s*\n?', '', html)
        
        # Remove any explanatory text before/after HTML
        lines = html.split('\n')
        start_idx = 0
        end_idx = len(lines)
        
        # Find actual HTML start
        for i, line in enumerate(lines):
            if line.strip().startswith('<!DOCTYPE') or line.strip().startswith('<html'):
                start_idx = i
                break
        
        # Find actual HTML end
        for i in range(len(lines) - 1, -1, -1):
            if '</html>' in lines[i]:
                end_idx = i + 1
                break
        
        return '\n'.join(lines[start_idx:end_idx]).strip()
    
    def _is_html_complete(self, html: str) -> bool:
        """Check if HTML document is complete"""
        html_lower = html.lower()
        
        required_elements = [
            '<!doctype',
            '<html',
            '<head',
            '</head>',
            '<body',
            '</body>',
            '</html>'
        ]
        
        return all(element in html_lower for element in required_elements)
    
    def _merge_continuation(self, initial_html: str, continuation: str) -> str:
        """Merge continuation HTML with initial HTML"""
        
        # Remove any duplicate DOCTYPE/html/head tags from continuation
        continuation = re.sub(r'<!DOCTYPE[^>]*>', '', continuation, flags=re.IGNORECASE)
        continuation = re.sub(r'<html[^>]*>', '', continuation, flags=re.IGNORECASE)
        continuation = re.sub(r'<head[^>]*>.*?</head>', '', continuation, flags=re.DOTALL | re.IGNORECASE)
        continuation = re.sub(r'<body[^>]*>', '', continuation, flags=re.IGNORECASE)

        initial_html = self._remove_incomplete_ending(initial_html)
        
        return initial_html + '\n' + continuation
    
    def _remove_incomplete_ending(self, html: str) -> str:
        """Remove incomplete tags from end of HTML"""
        lines = html.split('\n')
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.endswith('>') or line.endswith('}') or line.endswith(';'):
                return '\n'.join(lines[:i+1])
        
        return html
    
    def _ensure_html_completeness(self, html: str) -> str:
        """Ensure HTML document is properly structured"""
        
        if not html.strip():
            return html
        if '<!DOCTYPE' not in html.upper():
            html = '<!DOCTYPE html>\n' + html
        
        # Ensure closing tags
        if '</body>' not in html.lower():
            html += '\n</body>'
        if '</html>' not in html.lower():
            html += '\n</html>'
        
        return html

