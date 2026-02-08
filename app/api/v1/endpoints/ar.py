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
    # Fetch actual menu data from MinIO
    menu_filename = f"ar-menu-{menu_id}.json"
    object_name = minio_service.find_object_by_suffix(menu_filename)
    
    menu_items_json = "[]"
    if object_name:
        menu_bytes = minio_service.download_file(object_name)
        if menu_bytes:
            try:
                menu_data = json.loads(menu_bytes.decode('utf-8'))
                # Extract items and format for JavaScript
                items = menu_data.get('items', [])
                menu_items_json = json.dumps(items)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    
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
        .fallback-bg {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1f35 50%, #0a0e1a 100%);
            z-index: -1;
        }}
        .fallback-bg::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(0, 240, 255, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 70%, rgba(176, 0, 255, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.02) 0%, transparent 60%);
            animation: bgPulse 8s ease-in-out infinite;
        }}
        @keyframes bgPulse {{
            0%, 100% {{ opacity: 0.8; }}
            50% {{ opacity: 1; }}
        }}
        .no-camera-notice {{
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 165, 0, 0.2);
            border: 1px solid #ffa500;
            padding: 10px 20px;
            border-radius: 10px;
            color: #ffa500;
            font-size: 0.85rem;
            z-index: 1001;
            display: none;
            text-align: center;
        }}
        .no-camera-notice.visible {{ display: block; }}
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
            flex-wrap: wrap;
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
        .menu-card .category {{ font-size: 0.8rem; color: #00f0ff; opacity: 0.7; margin-bottom: 5px; }}
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
    <div class="fallback-bg" id="fallbackBg"></div>
    
    <div class="loading-screen" id="loadingScreen">
        <div class="spinner"></div>
        <p style="margin-top: 20px;">Initializing AR Experience...</p>
        <p style="opacity: 0.6; font-size: 0.9rem;">Please allow camera access</p>
    </div>

    <div class="no-camera-notice" id="noCameraNotice">
        📷 Camera not available - using 3D preview mode
    </div>

    <div class="ar-overlay">
        <h1>🍽️ AR Menu Experience</h1>
        <p>Point camera at menu items or scan QR codes</p>
    </div>

    <div class="menu-card" id="menuCard">
        <p class="category" id="itemCategory"></p>
        <h3 id="itemName">Menu Item</h3>
        <p class="price" id="itemPrice">$0.00</p>
        <p class="description" id="itemDesc">Description</p>
        <button class="ar-btn" onclick="hideCard()">Close</button>
    </div>

    <div class="ar-controls">
        <button class="ar-btn" onclick="showMenuItem()">🎲 Next Item</button>
        <button class="ar-btn" onclick="toggleCamera()">📷 Switch Camera</button>
        <button class="ar-btn" onclick="captureAR()">📸 Capture</button>
    </div>

    <a-scene 
        class="ar-scene"
        id="arScene"
        embedded
        vr-mode-ui="enabled: false"
        renderer="logarithmicDepthBuffer: true; antialias: true; alpha: true;"
    >
        <a-assets>
            <!-- Preload any assets here if needed -->
        </a-assets>
        
        <!-- Camera -->
        <a-camera position="0 1.6 0" look-controls="enabled: false"></a-camera>
        
        <!-- 3D Content Container -->
        <a-entity id="arContent" position="0 0.5 -3" visible="true">
            <!-- Base plate -->
            <a-cylinder 
                id="basePlate"
                position="0 0 0" 
                radius="0.5" 
                height="0.05" 
                color="#ffffff"
                material="metalness: 0.8; roughness: 0.2"
                animation="property: rotation; to: 0 360 0; loop: true; dur: 10000; easing: linear"
            ></a-cylinder>
            
            <!-- Dynamic 3D model container - will be populated by JS -->
            <a-entity id="foodModel" position="0 0.1 0"></a-entity>
            
            <!-- Price tag floating above -->
            <a-entity
                id="priceTag"
                position="0 0.8 0"
                text="value: ; align: center; width: 2; color: #00f0ff;"
                animation="property: position; to: 0 0.9 0; dir: alternate; loop: true; dur: 1000; easing: easeInOutSine"
            ></a-entity>
            
            <!-- Item name label -->
            <a-entity
                id="nameLabel"
                position="0 1.0 0"
                text="value: ; align: center; width: 3; color: #ffffff;"
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
        
        <!-- Sky for fallback mode -->
        <a-sky id="skySphere" color="#0a0e1a" visible="false"></a-sky>
    </a-scene>

    <script>
        const menuId = "{menu_id}";
        let currentItemIndex = 0;
        let hasCamera = true;
        
        // Menu items loaded from backend
        const menuItems = {menu_items_json};
        const displayItems = menuItems.length > 0 ? menuItems : [];
        
        // 3D model configurations based on item category/name keywords
        const modelConfigs = {{
            // Beverages
            tea: {{
                geometry: 'cylinder',
                props: {{ radius: 0.12, height: 0.2 }},
                color: '#8B4513',
                children: [
                    {{ geometry: 'cylinder', props: {{ radius: 0.14, height: 0.02 }}, position: '0 0.1 0', color: '#654321' }},
                    {{ geometry: 'torus', props: {{ radius: 0.08, radiusTubular: 0.015 }}, position: '0.15 0.05 0', rotation: '0 0 90', color: '#654321' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.08 }}, position: '0 0.12 0', color: '#D2691E', opacity: 0.6 }}
                ]
            }},
            coffee: {{
                geometry: 'cylinder',
                props: {{ radius: 0.1, height: 0.25 }},
                color: '#4a3728',
                children: [
                    {{ geometry: 'cylinder', props: {{ radius: 0.12, height: 0.02 }}, position: '0 0.12 0', color: '#3d2817' }},
                    {{ geometry: 'torus', props: {{ radius: 0.06, radiusTubular: 0.012 }}, position: '0.12 0.08 0', rotation: '0 0 90', color: '#3d2817' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.06 }}, position: '0 0.14 0', color: '#8B4513', opacity: 0.8 }}
                ]
            }},
            // Food
            burger: {{
                geometry: 'cylinder',
                props: {{ radius: 0.2, height: 0.08 }},
                color: '#D2691E',
                children: [
                    {{ geometry: 'cylinder', props: {{ radius: 0.18, height: 0.03 }}, position: '0 0.05 0', color: '#8B4513' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.19, height: 0.02 }}, position: '0 0.07 0', color: '#228B22' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.18, height: 0.02 }}, position: '0 0.09 0', color: '#FF6347' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.2, height: 0.06 }}, position: '0 0.13 0', color: '#D2691E' }}
                ]
            }},
            pizza: {{
                geometry: 'cylinder',
                props: {{ radius: 0.3, height: 0.03 }},
                color: '#F4A460',
                children: [
                    {{ geometry: 'sphere', props: {{ radius: 0.04 }}, position: '0.1 0.03 0.05', color: '#FF6347' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.04 }}, position: '-0.08 0.03 0.12', color: '#FF6347' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.04 }}, position: '0.05 0.03 -0.1', color: '#FF6347' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.03 }}, position: '-0.12 0.03 -0.05', color: '#228B22' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.03 }}, position: '0.15 0.03 -0.08', color: '#228B22' }}
                ]
            }},
            pasta: {{
                geometry: 'box',
                props: {{ width: 0.3, height: 0.08, depth: 0.2 }},
                color: '#F5DEB3',
                children: [
                    {{ geometry: 'sphere', props: {{ radius: 0.15 }}, position: '0 0.1 0', color: '#FFD700' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.03 }}, position: '0.08 0.18 0.05', color: '#FF6347' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.02 }}, position: '-0.05 0.16 -0.03', color: '#228B22' }}
                ]
            }},
            salad: {{
                geometry: 'cylinder',
                props: {{ radius: 0.25, height: 0.08 }},
                color: '#8FBC8F',
                children: [
                    {{ geometry: 'sphere', props: {{ radius: 0.06 }}, position: '0.08 0.08 0.05', color: '#228B22' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.05 }}, position: '-0.1 0.07 0.08', color: '#32CD32' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.04 }}, position: '0.05 0.09 -0.08', color: '#FF6347' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.03 }}, position: '-0.06 0.08 -0.05', color: '#FFD700' }}
                ]
            }},
            sushi: {{
                geometry: 'cylinder',
                props: {{ radius: 0.08, height: 0.05 }},
                color: '#2F4F4F',
                children: [
                    {{ geometry: 'box', props: {{ width: 0.14, height: 0.04, depth: 0.06 }}, position: '0 0.02 0', color: '#FFFAF0' }},
                    {{ geometry: 'box', props: {{ width: 0.12, height: 0.02, depth: 0.05 }}, position: '0 0.05 0', color: '#FA8072' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.08, height: 0.05 }}, position: '0.2 0 0', color: '#2F4F4F' }},
                    {{ geometry: 'box', props: {{ width: 0.14, height: 0.04, depth: 0.06 }}, position: '0.2 0.02 0', color: '#FFFAF0' }},
                    {{ geometry: 'box', props: {{ width: 0.12, height: 0.02, depth: 0.05 }}, position: '0.2 0.05 0', color: '#FA8072' }}
                ]
            }},
            steak: {{
                geometry: 'box',
                props: {{ width: 0.25, height: 0.05, depth: 0.18 }},
                color: '#8B0000',
                children: [
                    {{ geometry: 'box', props: {{ width: 0.22, height: 0.02, depth: 0.15 }}, position: '0 0.035 0', color: '#A52A2A' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.03, height: 0.01 }}, position: '0.12 0.03 0.1', color: '#FFD700' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.02 }}, position: '-0.1 0.04 0.08', color: '#228B22' }}
                ]
            }},
            soup: {{
                geometry: 'cylinder',
                props: {{ radius: 0.15, height: 0.12 }},
                color: '#FFFAF0',
                children: [
                    {{ geometry: 'cylinder', props: {{ radius: 0.13, height: 0.02 }}, position: '0 0.05 0', color: '#FFA500', opacity: 0.9 }},
                    {{ geometry: 'sphere', props: {{ radius: 0.02 }}, position: '0.05 0.07 0.03', color: '#228B22' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.015 }}, position: '-0.04 0.07 -0.02', color: '#228B22' }}
                ]
            }},
            cake: {{
                geometry: 'cylinder',
                props: {{ radius: 0.18, height: 0.15 }},
                color: '#DEB887',
                children: [
                    {{ geometry: 'cylinder', props: {{ radius: 0.19, height: 0.02 }}, position: '0 0.08 0', color: '#FFFAF0' }},
                    {{ geometry: 'cylinder', props: {{ radius: 0.02, height: 0.08 }}, position: '0 0.12 0', color: '#FF69B4' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.02 }}, position: '0 0.17 0', color: '#FFD700' }}
                ]
            }},
            dessert: {{
                geometry: 'cone',
                props: {{ radiusBottom: 0.08, radiusTop: 0, height: 0.2 }},
                color: '#D2691E',
                children: [
                    {{ geometry: 'sphere', props: {{ radius: 0.08 }}, position: '0 0.12 0', color: '#FFB6C1' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.06 }}, position: '0 0.2 0', color: '#FFFAF0' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.015 }}, position: '0.03 0.25 0.02', color: '#FF0000' }}
                ]
            }},
            sandwich: {{
                geometry: 'box',
                props: {{ width: 0.2, height: 0.12, depth: 0.12 }},
                color: '#F5DEB3',
                children: [
                    {{ geometry: 'box', props: {{ width: 0.18, height: 0.02, depth: 0.1 }}, position: '0 0.02 0', color: '#228B22' }},
                    {{ geometry: 'box', props: {{ width: 0.18, height: 0.02, depth: 0.1 }}, position: '0 0.04 0', color: '#FF6347' }},
                    {{ geometry: 'box', props: {{ width: 0.18, height: 0.02, depth: 0.1 }}, position: '0 0.06 0', color: '#FFD700' }}
                ]
            }},
            // Default
            default: {{
                geometry: 'sphere',
                props: {{ radius: 0.15 }},
                color: '#ff6b35',
                children: [
                    {{ geometry: 'sphere', props: {{ radius: 0.08 }}, position: '0.12 0.1 0', color: '#2ec4b6' }},
                    {{ geometry: 'sphere', props: {{ radius: 0.06 }}, position: '-0.08 0.08 0.08', color: '#e71d36' }}
                ]
            }}
        }};
        
        // Detect model type from item name/category
        function getModelType(item) {{
            const name = (item.name || '').toLowerCase();
            const category = (item.category || '').toLowerCase();
            const searchText = name + ' ' + category;
            
            const keywords = ['tea', 'coffee', 'burger', 'pizza', 'pasta', 'salad', 'sushi', 'steak', 'soup', 'cake', 'dessert', 'sandwich'];
            for (const keyword of keywords) {{
                if (searchText.includes(keyword)) {{
                    return keyword;
                }}
            }}
            
            // Additional mappings
            if (searchText.includes('latte') || searchText.includes('espresso') || searchText.includes('cappuccino')) return 'coffee';
            if (searchText.includes('beverage') || searchText.includes('drink') || searchText.includes('juice')) return 'tea';
            if (searchText.includes('ice cream') || searchText.includes('pudding') || searchText.includes('sweet')) return 'dessert';
            if (searchText.includes('noodle') || searchText.includes('spaghetti')) return 'pasta';
            if (searchText.includes('wrap') || searchText.includes('sub')) return 'sandwich';
            if (searchText.includes('beef') || searchText.includes('chicken') || searchText.includes('meat')) return 'steak';
            if (searchText.includes('fish') || searchText.includes('seafood')) return 'sushi';
            
            return 'default';
        }}
        
        // Build 3D model for item
        function buildModel(modelType) {{
            const config = modelConfigs[modelType] || modelConfigs.default;
            const container = document.getElementById('foodModel');
            
            // Clear existing model
            while (container.firstChild) {{
                container.removeChild(container.firstChild);
            }}
            
            // Create main geometry
            const mainEl = document.createElement('a-entity');
            mainEl.setAttribute('geometry', `primitive: ${{config.geometry}}; ${{Object.entries(config.props).map(([k,v]) => `${{k}}: ${{v}}`).join('; ')}}`);
            mainEl.setAttribute('material', `color: ${{config.color}}${{config.opacity ? `; opacity: ${{config.opacity}}; transparent: true` : ''}}`);
            container.appendChild(mainEl);
            
            // Create children
            if (config.children) {{
                config.children.forEach(child => {{
                    const childEl = document.createElement('a-entity');
                    childEl.setAttribute('geometry', `primitive: ${{child.geometry}}; ${{Object.entries(child.props).map(([k,v]) => `${{k}}: ${{v}}`).join('; ')}}`);
                    childEl.setAttribute('material', `color: ${{child.color}}${{child.opacity ? `; opacity: ${{child.opacity}}; transparent: true` : ''}}`);
                    if (child.position) childEl.setAttribute('position', child.position);
                    if (child.rotation) childEl.setAttribute('rotation', child.rotation);
                    container.appendChild(childEl);
                }});
            }}
        }}
        
        // Check camera availability
        async function checkCamera() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                stream.getTracks().forEach(track => track.stop());
                return true;
            }} catch (e) {{
                return false;
            }}
        }}
        
        // Initialize scene
        async function initScene() {{
            hasCamera = await checkCamera();
            
            if (!hasCamera) {{
                document.getElementById('noCameraNotice').classList.add('visible');
                document.getElementById('skySphere').setAttribute('visible', 'true');
                document.getElementById('fallbackBg').style.zIndex = '0';
            }}
            
            document.getElementById('loadingScreen').classList.add('hidden');
            
            // Show first item
            if (displayItems.length > 0) {{
                setTimeout(() => showMenuItem(), 500);
            }}
        }}
        
        // Hide loading screen when scene is ready
        document.querySelector('a-scene').addEventListener('loaded', function() {{
            setTimeout(initScene, 1000);
        }});
        
        function showMenuItem() {{
            if (displayItems.length === 0) {{
                document.getElementById('itemName').textContent = 'No menu items';
                document.getElementById('itemPrice').textContent = '';
                document.getElementById('itemDesc').textContent = 'Upload a menu to see items here';
                document.getElementById('itemCategory').textContent = '';
                document.getElementById('menuCard').classList.add('active');
                buildModel('default');
                return;
            }}
            
            const item = displayItems[currentItemIndex];
            currentItemIndex = (currentItemIndex + 1) % displayItems.length;
            
            document.getElementById('itemName').textContent = item.name || 'Menu Item';
            document.getElementById('itemPrice').textContent = item.price ? '$' + parseFloat(item.price).toFixed(2) : '';
            document.getElementById('itemDesc').textContent = item.description || '';
            document.getElementById('itemCategory').textContent = item.category ? `📁 ${{item.category}}` : '';
            document.getElementById('menuCard').classList.add('active');
            
            // Update 3D model based on item type
            const modelType = getModelType(item);
            buildModel(modelType);
            
            // Update price tag in 3D scene
            const priceTag = document.getElementById('priceTag');
            if (priceTag && item.price) {{
                priceTag.setAttribute('text', 'value: $' + parseFloat(item.price).toFixed(2) + '; align: center; width: 2; color: #00f0ff;');
            }}
            
            // Update name label
            const nameLabel = document.getElementById('nameLabel');
            if (nameLabel && item.name) {{
                nameLabel.setAttribute('text', 'value: ' + item.name + '; align: center; width: 3; color: #ffffff;');
            }}
            
            // Animate 3D content
            const arContent = document.getElementById('arContent');
            arContent.setAttribute('animation__pop', 'property: scale; from: 0.8 0.8 0.8; to: 1 1 1; dur: 300; easing: easeOutBack');
        }}
        
        function hideCard() {{
            document.getElementById('menuCard').classList.remove('active');
        }}
        
        function toggleCamera() {{
            if (!hasCamera) {{
                alert('Camera not available on this device');
                return;
            }}
            alert('Camera switching - feature available on mobile devices');
        }}
        
        function captureAR() {{
            const scene = document.querySelector('a-scene');
            if (scene && scene.components && scene.components.screenshot) {{
                const canvas = scene.components.screenshot.getCanvas('perspective');
                if (canvas) {{
                    const link = document.createElement('a');
                    link.download = 'ar-menu-capture.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    return;
                }}
            }}
            alert('Screenshot captured! (Check downloads)');
        }}
        
        // Listen for marker detection
        document.addEventListener('markerFound', function(e) {{
            showMenuItem();
        }});
    </script>
</body>
</html>'''
    return HTMLResponse(content=html_content)
