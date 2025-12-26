/**
 * XSS Protection Utilities
 * Provides functions to sanitize and escape user input to prevent XSS attacks
 */

/**
 * Escape HTML entities to prevent XSS
 * @param text - The text to escape
 * @returns Escaped text safe for HTML insertion
 */
export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Highlight keywords in text with XSS protection
 * @param text - The original text
 * @param keyword - The keyword to highlight
 * @param highlightClass - CSS class for highlighted text
 * @returns HTML string with highlighted keyword (XSS-safe)
 */
export function highlightKeyword(
  text: string,
  keyword: string,
  highlightClass: string = 'highlight'
): string {
  if (!keyword) return escapeHtml(text)
  
  const escapedText = escapeHtml(text)
  const escapedKeyword = escapeHtml(keyword)
  
  // Use case-insensitive replace
  const regex = new RegExp(escapedKeyword, 'gi')
  return escapedText.replace(
    regex,
    (match) => `<span class="${highlightClass}">${match}</span>`
  )
}

/**
 * Sanitize HTML content to remove potentially dangerous elements and attributes
 * @param html - The HTML content to sanitize
 * @returns Sanitized HTML
 */
export function sanitizeHtml(html: string): string {
  // Create a temporary div to parse HTML
  const temp = document.createElement('div')
  temp.innerHTML = html
  
  // List of allowed tags
  const allowedTags = ['b', 'i', 'u', 'strong', 'em', 'span', 'p', 'br', 'a']
  
  // List of allowed attributes
  const allowedAttrs = ['class', 'href', 'title']
  
  // Remove disallowed tags and attributes
  const sanitize = (node: Node): void => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element
      
      // Check if tag is allowed
      if (!allowedTags.includes(element.tagName.toLowerCase())) {
        // Replace with text content
        const textNode = document.createTextNode(element.textContent || '')
        element.parentNode?.replaceChild(textNode, element)
        return
      }
      
      // Remove disallowed attributes
      Array.from(element.attributes).forEach((attr) => {
        if (!allowedAttrs.includes(attr.name.toLowerCase())) {
          element.removeAttribute(attr.name)
        }
      })
      
      // For links, ensure they don't use javascript: protocol
      if (element.tagName.toLowerCase() === 'a') {
        const href = element.getAttribute('href') || ''
        if (href.toLowerCase().startsWith('javascript:')) {
          element.removeAttribute('href')
        }
      }
    }
    
    // Recursively sanitize child nodes
    Array.from(node.childNodes).forEach(sanitize)
  }
  
  sanitize(temp)
  return temp.innerHTML
}
