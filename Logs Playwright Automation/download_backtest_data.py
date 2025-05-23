import os
import time
from playwright.sync_api import Playwright, sync_playwright

def save_debug_screenshot(page, step_name, download_dir):
    """Save a screenshot with a descriptive name"""
    try:
        timestamp = int(time.time())
        filename = f"debug_{step_name}_{timestamp}.png"
        path = os.path.join(download_dir, filename)
        page.screenshot(path=path)
        print(f"Debug screenshot saved: {path}")
        return path
    except Exception as e:
        print(f"Error saving debug screenshot: {e}")
        return None

def scroll_to_element(page, selector, context="", download_dir=None, timeout=10000):
    """Scroll to make sure element is in view"""
    debug_id = f"{context}_{int(time.time())}" if context else str(int(time.time()))
    print(f"\n[DEBUG {debug_id}] Scrolling to element: {selector}")
    
    try:
        # First take a screenshot before any scrolling
        save_debug_screenshot(page, f"before_scroll_{debug_id}", download_dir)
        
        # Try to find the element with a longer timeout
        print(f"[DEBUG {debug_id}] Waiting for element to be attached...")
        element = page.wait_for_selector(selector, state='attached', timeout=timeout)
        
        # Take screenshot after finding the element
        save_debug_screenshot(page, f"element_found_{debug_id}", download_dir)
        
        # Get element position for debugging
        try:
            box = element.bounding_box()
            print(f"[DEBUG {debug_id}] Element position - x: {box['x']}, y: {box['y']}, width: {box['width']}, height: {box['height']}")
        except Exception as e:
            print(f"[DEBUG {debug_id}] Could not get element position: {e}")
        
        # Scroll to the element
        print(f"[DEBUG {debug_id}] Scrolling element into view...")
        element.scroll_into_view_if_needed()
        page.wait_for_timeout(500)  # Wait for scroll to complete
        
        # Scroll a bit more to ensure it's fully in view (sometimes needed for fixed headers)
        print("[DEBUG {debug_id}] Adjusting scroll position...")
        page.evaluate("window.scrollBy(0, -100)")
        page.wait_for_timeout(300)
        
        # Take screenshot after scrolling
        save_debug_screenshot(page, f"after_scroll_{debug_id}", download_dir)
        
        # Check if element is visible
        is_visible = element.is_visible()
        print(f"[DEBUG {debug_id}] Is element visible? {is_visible}")
        
        if not is_visible:
            print("[DEBUG {debug_id}] Element not visible after scrolling, trying to make it visible...")
            page.evaluate("arguments[0].scrollIntoView({block: 'center'})", element)
            page.wait_for_timeout(500)
            
            # Take another screenshot after adjustment
            save_debug_screenshot(page, f"after_adjustment_{debug_id}", download_dir)
            
        # Final check
        is_visible = element.is_visible()
        print(f"[DEBUG {debug_id}] Final visibility check: {is_visible}")
        
        if not is_visible:
            print("[DEBUG {debug_id}] WARNING: Element still not visible after all attempts!")
            
        return element
        
    except Exception as e:
        print(f"[DEBUG {debug_id}] ERROR in scroll_to_element: {str(e)}")
        print("[DEBUG {debug_id}] Page content (first 1000 chars):")
        print(page.content()[:1000])
        
        # Take a screenshot of the full page
        try:
            full_page_path = os.path.join(download_dir, f"fullpage_error_{debug_id}.png")
            page.screenshot(path=full_page_path, full_page=True)
            print(f"[DEBUG {debug_id}] Full page screenshot saved to: {full_page_path}")
        except Exception as screenshot_error:
            print(f"[DEBUG {debug_id}] Failed to take full page screenshot: {screenshot_error}")
            
        return None

def wait_and_click(page, selector, context="", download_dir=None, max_attempts=3, timeout=10000):
    """Helper function to wait for an element and click it"""
    debug_id = f"{context}_{int(time.time())}" if context else str(int(time.time()))
    
    for attempt in range(max_attempts):
        try:
            print(f"\n[DEBUG {debug_id}] Attempt {attempt + 1}/{max_attempts} - Waiting for element: {selector}")
            
            # First scroll to the element with debugging context
            element = scroll_to_element(
                page, 
                selector, 
                context=f"{context}_attempt{attempt+1}",
                download_dir=download_dir,
                timeout=timeout
            )
            
            if not element:
                error_msg = f"[DEBUG {debug_id}] Could not find element: {selector}"
                print(error_msg)
                raise Exception(error_msg)
            
            # Wait for the element to be clickable
            print(f"[DEBUG {debug_id}] Waiting for element to be clickable...")
            element = page.wait_for_selector(selector, state='visible', timeout=timeout)
            
            # Add a small highlight to see what's being clicked (for debugging)
            try:
                highlight_js = """
                (selector) => {
                    const style = document.createElement('style');
                    style.textContent = `
                        .highlighted-element {
                            outline: 3px solid #ff0000 !important;
                            background-color: rgba(255, 0, 0, 0.2) !important;
                            transition: all 0.3s ease;
                            box-shadow: 0 0 10px 5px rgba(255, 0, 0, 0.5) !important;
                            position: relative;
                            z-index: 9999 !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.classList.add('highlighted-element');
                        setTimeout(() => el.classList.remove('highlighted-element'), 1500);
                    });
                    
                    return elements.length;
                }
                """
                highlighted = page.evaluate(highlight_js, selector)
                print(f"[DEBUG {debug_id}] Highlighted {highlighted} element(s)")
                
                # Take a screenshot after highlighting
                save_debug_screenshot(page, f"highlight_{debug_id}", download_dir)
                
            except Exception as e:
                print(f"[DEBUG {debug_id}] Error during highlighting: {e}")
            
            # Click the element
            print(f"[DEBUG {debug_id}] Clicking element...")
            
            # Try different click methods
            try:
                # Method 1: Standard click
                element.click(delay=100)
                print(f"[DEBUG {debug_id}] Standard click successful")
            except Exception as click_error:
                print(f"[DEBUG {debug_id}] Standard click failed, trying JavaScript click: {click_error}")
                try:
                    # Method 2: JavaScript click
                    page.evaluate("el => el.click()", element)
                    print(f"[DEBUG {debug_id}] JavaScript click successful")
                except Exception as js_click_error:
                    print(f"[DEBUG {debug_id}] JavaScript click failed, trying coordinates: {js_click_error}")
                    # Method 3: Click using coordinates
                    box = element.bounding_box()
                    page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    print(f"[DEBUG {debug_id}] Coordinate click successful")
            
            # Small delay after click
            time.sleep(1.5)
            
            # Take a screenshot after clicking
            save_debug_screenshot(page, f"after_click_{debug_id}", download_dir)
            
            return True
            
        except Exception as e:
            error_msg = f"[DEBUG {debug_id}] Attempt {attempt + 1} failed: {str(e)}"
            print(error_msg)
            
            # Save error screenshot
            error_screenshot = os.path.join(download_dir, f"error_attempt{attempt+1}_{debug_id}.png")
            try:
                page.screenshot(path=error_screenshot, full_page=True)
                print(f"[DEBUG {debug_id}] Error screenshot saved to: {error_screenshot}")
            except Exception as screenshot_error:
                print(f"[DEBUG {debug_id}] Failed to save error screenshot: {screenshot_error}")
            
            if attempt == max_attempts - 1:  # Last attempt
                print(f"[DEBUG {debug_id}] Failed to click element after {max_attempts} attempts")
                return False
                
            # Wait a bit before retrying, increasing delay with each attempt
            retry_delay = (attempt + 1) * 2
            print(f"[DEBUG {debug_id}] Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
    
    return False

def run(playwright: Playwright, backtest_url: str, download_dir: str = None) -> None:
    # Set up download directory
    download_dir = download_dir or os.path.join(os.getcwd(), 'downloads')
    os.makedirs(download_dir, exist_ok=True)
    print(f"[INIT] Downloads will be saved to: {download_dir}")
    
    # Create a debug directory for this run
    debug_dir = os.path.join(download_dir, f"debug_{int(time.time())}")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"[INIT] Debug files will be saved to: {debug_dir}")
    
    # Browser launch configuration
    browser = playwright.chromium.launch(
        headless=False,
        downloads_path=download_dir,
        slow_mo=100,  # Slow down operations to make them more reliable
        devtools=True  # Open devtools for debugging
    )
    
    # Use saved storage state if it exists
    storage_state = "qc_auth.json"
    context = browser.new_context(
        storage_state=storage_state if os.path.exists(storage_state) else None,
        accept_downloads=True,
        viewport={'width': 1920, 'height': 1080},  # Set a consistent viewport
        record_video_dir=debug_dir  # Record video of the session
    )
    
    # Enable request/response logging
    def log_request(request):
        print(f"> {request.method} {request.url}")
    
    def log_response(response):
        print(f"< {response.status} {response.url}")
    
    page = context.new_page()
    
    # Enable request/response logging
    page.on("request", log_request)
    page.on("response", log_response)
    
    # Log console messages
    def log_console(msg):
        print(f"[CONSOLE] {msg.text}")
    
    page.on("console", log_console)
    
    # Log page errors
    def log_page_error(error):
        print(f"[PAGE ERROR] {error}")
    
    page.on("pageerror", log_page_error)
    
    try:
        # Navigate to the backtest URL
        print(f"Navigating to: {backtest_url}")
        page.goto(backtest_url, wait_until="networkidle")
        
        # Wait for the page to fully load
        print("Waiting for page to load...")
        page.wait_for_load_state("networkidle")
        
        # Debug information
        print(f"Page title: {page.title()}")
        print(f"Current URL: {page.url}")
        
        # Take a screenshot for debugging
        screenshot_path = os.path.join(download_dir, "page_debug.png")
        page.screenshot(path=screenshot_path)
        print(f"Debug screenshot saved as {screenshot_path}")
        
        # Wait for the main content to load
        print("Waiting for backtest content...")
        try:
            # Try to find any of these elements that might contain the backtest content
            content_selector = "#code-frame, .backtest-container, .backtest-body, .backtest, .container"
            page.wait_for_selector(content_selector, state="visible", timeout=15000)
            print("Found backtest content")
            
            # Take another screenshot after content loads
            page.screenshot(path=os.path.join(download_dir, "content_loaded.png"))
            
        except Exception as e:
            print(f"Warning: Could not find expected elements: {e}")
            print("Page content:", page.content()[:1000])  # Print first 1000 chars of page content
            raise
        
        # Download logs
        print("\n--- Downloading logs ---")
        try:
            # First, scroll to the bottom to load any lazy-loaded content
            print("Scrolling to bottom to ensure all content is loaded...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Wait for any lazy loading
            
            # Try different possible selectors for the Logs tab
            logs_selectors = [
                "a:has-text('Logs')",
                ".logs-tab",
                "[data-testid='logs-tab']",
                "//*[contains(@class, 'tab') and contains(., 'Logs')]",
                "//a[contains(., 'Logs')]"
            ]
            
            logs_clicked = False
            for selector in logs_selectors:
                print(f"Trying selector: {selector}")
                if wait_and_click(page, selector):
                    logs_clicked = True
                    break
                    
            if not logs_clicked:
                raise Exception("Could not find or click the Logs tab")
            
            # Wait for logs to load
            time.sleep(2)
            
            # Try different possible selectors for the download button
            download_selectors = [
                "a:has-text('Download Logs')",
                "button:has-text('Download Logs')",
                ".download-logs",
                "[data-testid='download-logs']",
                "//a[contains(., 'Download Logs')]"
            ]
            
            download_clicked = False
            for selector in download_selectors:
                print(f"Trying download selector: {selector}")
                if wait_and_click(page, selector):
                    download_clicked = True
                    break
                    
            if not download_clicked:
                raise Exception("Could not find or click the Download Logs button")
            
            # Wait for download to start
            with page.expect_download() as download_info:
                print("Waiting for download to start...")
                download = download_info.value
                
                # Save the file
                filename = f"logs_{os.path.basename(backtest_url.rstrip('/'))}.txt"
                download_path = os.path.join(download_dir, filename)
                download.save_as(download_path)
                print(f"Downloaded logs to: {download_path}")
                
        except Exception as e:
            print(f"Error downloading logs: {e}")
            page.screenshot(path=os.path.join(download_dir, "error_logs.png"))
        
        # Download orders
        print("\n--- Downloading orders ---")
        try:
            # Scroll to top first
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            # Try different possible selectors for the Orders tab
            orders_selectors = [
                "a:has-text('Orders')",
                ".orders-tab",
                "[data-testid='orders-tab']",
                "//*[contains(@class, 'tab') and contains(., 'Orders')]",
                "//a[contains(., 'Orders')]"
            ]
            
            orders_clicked = False
            for selector in orders_selectors:
                print(f"Trying selector: {selector}")
                if wait_and_click(page, selector):
                    orders_clicked = True
                    break
                    
            if not orders_clicked:
                raise Exception("Could not find or click the Orders tab")
            
            # Wait for orders to load
            time.sleep(2)
            
            # Try different possible selectors for the download button
            download_selectors = [
                "a:has-text('Download Orders')",
                "button:has-text('Download Orders')",
                ".download-orders",
                "[data-testid='download-orders']",
                "//a[contains(., 'Download Orders')]"
            ]
            
            download_clicked = False
            for selector in download_selectors:
                print(f"Trying download selector: {selector}")
                if wait_and_click(page, selector):
                    download_clicked = True
                    break
                    
            if not download_clicked:
                raise Exception("Could not find or click the Download Orders button")
            
            # Wait for download to start
            with page.expect_download() as download_info:
                print("Waiting for orders download to start...")
                download = download_info.value
                
                # Save the file
                filename = f"orders_{os.path.basename(backtest_url.rstrip('/'))}.csv"
                download_path = os.path.join(download_dir, filename)
                download.save_as(download_path)
                print(f"Downloaded orders to: {download_path}")
                
        except Exception as e:
            print(f"Error downloading orders: {e}")
            page.screenshot(path=os.path.join(download_dir, "error_orders.png"))
        
        print("\n--- Script completed ---")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        # Take a screenshot if something goes wrong
        error_screenshot = os.path.join(download_dir, "error_screenshot.png")
        page.screenshot(path=error_screenshot)
        print(f"Screenshot saved as {error_screenshot}")
        raise  # Re-raise the exception to see full traceback
    
    finally:
        # Keep browser open for inspection
        print("\nPress Enter to close the browser...")
        input()
        context.close()
        browser.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Download QuantConnect backtest data')
    parser.add_argument('url', nargs='?', 
                       default='https://www.quantconnect.com/project/23136343',
                       help='QuantConnect backtest URL')
    parser.add_argument('--download-dir', '-d', 
                       default='downloads',
                       help='Directory to save downloaded files (default: ./downloads)')
    
    args = parser.parse_args()
    
    with sync_playwright() as playwright:
        run(playwright, args.url, args.download_dir)
