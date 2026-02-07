from fastapi import APIRouter, Depends, UploadFile, File as FileParam, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.services.minio_service import minio_service
from app.services.ar_menu_service import ar_menu_service
from app.services.pdf_service import pdf_service
import json

router = APIRouter(prefix="/ar", tags=["AR Menu"])

@router.post("/menu/create", response_model=dict)
async def create_ar_menu(
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if file.content_type not in ["text/csv", "application/json"]:
        raise HTTPException(status_code=400, detail="Only CSV/JSON supported")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Parse menu data
        menu_items = ar_menu_service.parse_menu_data(content, file.content_type)
        
        # Generate AR menu
        ar_menu = ar_menu_service.generate_ar_menu(menu_items)
        
        # Save AR menu JSON
        menu_json = json.dumps(ar_menu, indent=2).encode('utf-8')
        menu_filename = f"ar-menu-{ar_menu['id']}.json"
        menu_object_name = minio_service.upload_file(
            filename=menu_filename,
            file_content=menu_json,
            metadata={'type': 'ar_menu_json', 'user_id': str(current_user.id)}
        )
        
        # Save preview image
        preview_image = ar_menu_service.generate_preview(menu_items)
        preview_filename = f"ar-menu-preview-{ar_menu['id']}.png"
        preview_object_name = minio_service.upload_file(
            filename=preview_filename,
            file_content=preview_image,
            metadata={'type': 'ar_menu_preview'}
        )
        preview_url = minio_service.get_presigned_url(preview_object_name)
        
        # Save to database
        db_file = FileModel(
            filename=menu_filename,
            user_id=current_user.id,
            object_name=menu_object_name,
            mime_type="application/json",
            size_bytes=len(menu_json)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        # Generate AR viewer URL
        ar_viewer_url = f"/api/v1/ar/viewer/{ar_menu['id']}"
        
        return {
            "ar_menu_id": db_file.id,
            "preview_url": preview_url,
            "item_count": len(menu_items),
            "qr_count": len(ar_menu['qr_codes']),
            "menu_url": minio_service.get_presigned_url(menu_object_name),
            "ar_viewer_url": ar_viewer_url,
            "ar_data": ar_menu  # Include full AR data for client-side rendering
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AR menu generation failed: {str(e)}")


@router.get("/viewer/{menu_id}", response_class=HTMLResponse)
async def ar_viewer(menu_id: str):
    """
    Serve an AR viewer page using AR.js and A-Frame.
    This creates an immersive AR experience where users can view menu items in 3D.
    """
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>AR Menu Viewer</title>
    <script src="https://aframe.io/releases/1.4.0/aframe.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mind-ar@1.2.2/dist/mindar-image-aframe.prod.js"></script>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .ar-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            padding: 20px;
            background: linear-gradient(180deg, rgba(0,0,0,0.8) 0%, transparent 100%);
            color: white;
            z-index: 1000;
            text-align: center;
        }}
        .ar-overlay h1 {{ margin: 0; font-size: 1.5rem; text-shadow: 0 0 10px #00f0ff; }}
        .ar-overlay p {{ margin: 5px 0 0; opacity: 0.8; font-size: 0.9rem; }}
        .ar-controls {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 20px;
            background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, transparent 100%);
            z-index: 1000;
            display: flex;
            justify-content: center;
            gap: 15px;
        }}
        .ar-btn {{
            background: linear-gradient(135deg, #00f0ff, #b000ff);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 1rem;
            cursor: pointer;
            box-shadow: 0 0 20px rgba(0,240,255,0.5);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .ar-btn:hover {{ transform: scale(1.05); box-shadow: 0 0 30px rgba(0,240,255,0.8); }}
        .menu-card {{
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(20, 24, 36, 0.95);
            border: 1px solid #00f0ff;
            border-radius: 15px;
            padding: 20px;
            color: white;
            max-width: 300px;
            z-index: 999;
            box-shadow: 0 0 30px rgba(0,240,255,0.3);
            display: none;
        }}
        .menu-card.active {{ display: block; animation: slideUp 0.3s ease; }}
        .menu-card h3 {{ margin: 0 0 10px; color: #00f0ff; }}
        .menu-card .price {{ font-size: 1.5rem; color: #b000ff; font-weight: bold; }}
        .menu-card .description {{ opacity: 0.8; margin: 10px 0; }}
        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateX(-50%) translateY(20px); }}
            to {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
        }}
        .loading-screen {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #0a0e1a;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            color: white;
        }}
        .loading-screen.hidden {{ display: none; }}
        .spinner {{
            width: 60px;
            height: 60px;
            border: 3px solid transparent;
            border-top: 3px solid #00f0ff;
            border-right: 3px solid #b000ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
        .ar-scene {{ width: 100vw; height: 100vh; }}
    </style>
</head>
<body>
    <div class="loading-screen" id="loadingScreen">
        <div class="spinner"></div>
        <p style="margin-top: 20px;">Initializing AR Experience...</p>
        <p style="opacity: 0.6; font-size: 0.9rem;">Please allow camera access</p>
    </div>

    <div class="ar-overlay">
        <h1>🍽️ AR Menu Experience</h1>
        <p>Point camera at menu items or scan QR codes</p>
    </div>

    <div class="menu-card" id="menuCard">
        <h3 id="itemName">Menu Item</h3>
        <p class="price" id="itemPrice">$0.00</p>
        <p class="description" id="itemDesc">Description</p>
        <button class="ar-btn" onclick="hideCard()">Close</button>
    </div>

    <div class="ar-controls">
        <button class="ar-btn" onclick="showDemoItem()">🎲 Demo Item</button>
        <button class="ar-btn" onclick="toggleCamera()">📷 Switch Camera</button>
        <button class="ar-btn" onclick="captureAR()">📸 Capture</button>
    </div>

    <a-scene 
        class="ar-scene"
        embedded
        arjs="sourceType: webcam; debugUIEnabled: false; detectionMode: mono_and_matrix; matrixCodeType: 3x3;"
        vr-mode-ui="enabled: false"
        renderer="logarithmicDepthBuffer: true; antialias: true; alpha: true;"
        gesture-detector
    >
        <!-- Camera -->
        <a-camera gps-camera rotation-reader></a-camera>
        
        <!-- Demo 3D Content - Floating menu item -->
        <a-entity id="arContent" position="0 0 -3" visible="true">
            <!-- Floating plate -->
            <a-cylinder 
                position="0 0 0" 
                radius="0.5" 
                height="0.05" 
                color="#ffffff"
                material="metalness: 0.8; roughness: 0.2"
                animation="property: rotation; to: 0 360 0; loop: true; dur: 10000; easing: linear"
            ></a-cylinder>
            
            <!-- Food item representation -->
            <a-sphere 
                position="0 0.15 0" 
                radius="0.2" 
                color="#ff6b35"
                material="metalness: 0.3; roughness: 0.7"
            ></a-sphere>
            <a-sphere 
                position="0.15 0.25 0" 
                radius="0.1" 
                color="#2ec4b6"
            ></a-sphere>
            <a-sphere 
                position="-0.1 0.22 0.1" 
                radius="0.08" 
                color="#e71d36"
            ></a-sphere>
            
            <!-- Price tag floating above -->
            <a-entity
                position="0 0.6 0"
                text="value: $12.99; align: center; width: 2; color: #00f0ff;"
                animation="property: position; to: 0 0.7 0; dir: alternate; loop: true; dur: 1000; easing: easeInOutSine"
            ></a-entity>
            
            <!-- Glow ring -->
            <a-torus 
                position="0 0.02 0"
                rotation="90 0 0"
                radius="0.6"
                radius-tubular="0.01"
                color="#00f0ff"
                material="emissive: #00f0ff; emissiveIntensity: 0.5"
                animation="property: scale; to: 1.1 1.1 1.1; dir: alternate; loop: true; dur: 2000; easing: easeInOutSine"
            ></a-torus>
        </a-entity>
        
        <!-- Lighting -->
        <a-light type="ambient" color="#ffffff" intensity="0.6"></a-light>
        <a-light type="directional" color="#ffffff" intensity="0.8" position="1 2 1"></a-light>
        <a-light type="point" color="#00f0ff" intensity="0.5" position="0 2 -3"></a-light>
    </a-scene>

    <script>
        const menuId = "{menu_id}";
        let menuData = null;
        let currentItemIndex = 0;
        
        // Demo menu items (would be loaded from API in production)
        const demoItems = [
            {{ name: "Gourmet Burger", price: 15.99, description: "Premium beef patty with artisan toppings" }},
            {{ name: "Truffle Pasta", price: 24.99, description: "Fresh pasta with black truffle cream sauce" }},
            {{ name: "Sushi Platter", price: 32.99, description: "Chef's selection of premium sushi" }},
            {{ name: "Caesar Salad", price: 12.99, description: "Crisp romaine with house-made dressing" }},
            {{ name: "Chocolate Lava Cake", price: 9.99, description: "Warm chocolate cake with molten center" }}
        ];
        
        // Hide loading screen when scene is ready
        document.querySelector('a-scene').addEventListener('loaded', function() {{
            setTimeout(() => {{
                document.getElementById('loadingScreen').classList.add('hidden');
            }}, 1500);
        }});
        
        function showDemoItem() {{
            const item = demoItems[currentItemIndex];
            currentItemIndex = (currentItemIndex + 1) % demoItems.length;
            
            document.getElementById('itemName').textContent = item.name;
            document.getElementById('itemPrice').textContent = '$' + item.price.toFixed(2);
            document.getElementById('itemDesc').textContent = item.description;
            document.getElementById('menuCard').classList.add('active');
            
            // Animate 3D content
            const arContent = document.getElementById('arContent');
            arContent.setAttribute('animation__pop', 'property: scale; from: 0.8 0.8 0.8; to: 1 1 1; dur: 300; easing: easeOutBack');
        }}
        
        function hideCard() {{
            document.getElementById('menuCard').classList.remove('active');
        }}
        
        function toggleCamera() {{
            // Toggle between front and back camera
            alert('Camera switching - feature available on mobile devices');
        }}
        
        function captureAR() {{
            // Capture current AR view
            const canvas = document.querySelector('a-scene').components.screenshot.getCanvas('perspective');
            if (canvas) {{
                const link = document.createElement('a');
                link.download = 'ar-menu-capture.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }} else {{
                alert('AR Capture ready! (Screenshot API)');
            }}
        }}
        
        // Listen for marker detection
        document.addEventListener('markerFound', function(e) {{
            showDemoItem();
        }});
    </script>
</body>
</html>'''
    return HTMLResponse(content=html_content)
