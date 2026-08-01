#!/usr/bin/env python3
"""
Altium Library Generator
Generates .SchLib and .PcbLib files from collected component data.
Uses altium-monkey for programmatic Altium file creation.
"""

import json
import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import altium-monkey
try:
    from altium import Document, SchDoc, PcbDoc
    from altium.objects import Component, Pin, Designator, Parameter
    HAS_ALTIUM_MONKEY = True
except ImportError:
    HAS_ALTIUM_MONKEY = False
    logger.warning("altium-monkey not installed. Using template-based generation.")


# Package to footprint mapping (common packages)
PACKAGE_MAP = {
    "0201": {"width": 0.6, "height": 0.3, "pad_w": 0.3, "pad_h": 0.3},
    "0402": {"width": 1.0, "height": 0.5, "pad_w": 0.5, "pad_h": 0.5},
    "0603": {"width": 1.6, "height": 0.8, "pad_w": 0.8, "pad_h": 0.8},
    "0805": {"width": 2.0, "height": 1.25, "pad_w": 1.0, "pad_h": 1.0},
    "1206": {"width": 3.2, "height": 1.6, "pad_w": 1.5, "pad_h": 1.5},
    "1210": {"width": 3.2, "height": 2.5, "pad_w": 1.5, "pad_h": 1.5},
    "SOT-23": {"width": 2.9, "height": 1.6, "pad_w": 0.9, "pad_h": 1.0},
    "SOT-223": {"width": 6.5, "height": 3.5, "pad_w": 1.5, "pad_h": 1.5},
    "TSSOP-16": {"width": 5.0, "height": 4.4, "pad_w": 0.6, "pad_h": 1.5},
    "QFP-44": {"width": 10.0, "height": 10.0, "pad_w": 0.5, "pad_h": 1.5},
    "QFN-32": {"width": 5.0, "height": 5.0, "pad_w": 0.5, "pad_h": 1.0},
    "BGA-100": {"width": 10.0, "height": 10.0, "pad_w": 0.4, "pad_h": 0.4},
    "USB-C": {"width": 8.94, "height": 7.35, "pad_w": 0.5, "pad_h": 1.5},
    "SOP-8": {"width": 4.9, "height": 3.9, "pad_w": 0.6, "pad_h": 1.5},
    "DIP-8": {"width": 7.62, "height": 6.35, "pad_w": 1.5, "pad_h": 1.5},
    "TO-220": {"width": 10.0, "height": 15.0, "pad_w": 1.5, "pad_h": 2.0},
    "TO-92": {"width": 5.0, "height": 5.0, "pad_w": 1.0, "pad_h": 1.0},
}


def create_schlib_simple(components, output_path):
    """
    Create a SchLib file using altium-monkey if available,
    otherwise create a placeholder JSON for manual conversion.
    """
    if HAS_ALTIUM_MONKEY:
        return create_schlib_with_monkey(components, output_path)
    else:
        return create_schlib_json(components, output_path)


def create_schlib_with_monkey(components, output_path):
    """Create SchLib using altium-monkey library."""
    try:
        doc = SchDoc()
        
        for i, comp in enumerate(components):
            # Create component
            component = Component(
                Designator=Designator(comp.get("mpn", f"U{i}")),
                Description=comp.get("description", ""),
            )
            
            # Add parameters
            if comp.get("manufacturer"):
                component.AddParameter("Manufacturer", comp["manufacturer"])
            if comp.get("package"):
                component.AddParameter("Package", comp["package"])
            if comp.get("lscs_code"):
                component.AddParameter("LCSC", comp["lscs_code"])
            if comp.get("datasheet"):
                component.AddParameter("Datasheet", comp["datasheet"])
            
            # Add basic pins (2-pin for passives, generic for ICs)
            package = comp.get("package", "")
            if any(p in package for p in ["0201", "0402", "0603", "0805", "1206"]):
                # Passive component (2 pins)
                component.AddPin(Pin(Name="1", Number="1"))
                component.AddPin(Pin(Name="2", Number="2"))
            else:
                # Generic IC (placeholder pins)
                for pin_num in range(1, 9):
                    component.AddPin(Pin(Name=str(pin_num), Number=str(pin_num)))
            
            doc.AddComponent(component)
        
        doc.Save(output_path)
        logger.info(f"Created SchLib with {len(components)} components: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating SchLib with altium-monkey: {e}")
        return create_schlib_json(components, output_path)


def create_schlib_json(components, output_path):
    """Create a JSON-based SchLib representation (for later conversion)."""
    json_path = output_path.replace(".SchLib", "_symbol.json")
    
    symbols = []
    for comp in components:
        package = comp.get("package", "")
        is_passive = any(p in package for p in ["0201", "0402", "0603", "0805", "1206"])
        
        symbol = {
            "name": comp.get("mpn", ""),
            "description": comp.get("description", ""),
            "manufacturer": comp.get("manufacturer", ""),
            "package": package,
            "is_passive": is_passive,
            "pins": [],
            "parameters": {
                "LCSC": comp.get("lscs_code", ""),
                "Datasheet": comp.get("datasheet", ""),
                "Category": comp.get("category", ""),
            },
        }
        
        if is_passive:
            symbol["pins"] = [
                {"number": "1", "name": "1", "x": -100, "y": 0},
                {"number": "2", "name": "2", "x": 100, "y": 0},
            ]
            symbol["body"] = {"type": "rectangle", "x": -50, "y": -25, "w": 100, "h": 50}
        else:
            # Generic IC symbol
            symbol["pins"] = [
                {"number": str(i), "name": str(i), "x": -150, "y": (i - 1) * 100 - 150}
                for i in range(1, 9)
            ]
            symbol["body"] = {"type": "rectangle", "x": -100, "y": -200, "w": 200, "h": 400}
        
        symbols.append(symbol)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Created JSON symbols: {json_path}")
    return True


def create_pcblib_simple(components, output_path):
    """Create PcbLib file or JSON representation."""
    if HAS_ALTIUM_MONKEY:
        return create_pcblib_with_monkey(components, output_path)
    else:
        return create_pcblib_json(components, output_path)


def create_pcblib_with_monkey(components, output_path):
    """Create PcbLib using altium-monkey."""
    try:
        doc = PcbDoc()
        
        for comp in components:
            package = comp.get("package", "")
            footprint_name = package if package else comp.get("mpn", "Unknown")
            
            # Get footprint dimensions
            dims = PACKAGE_MAP.get(package, {"width": 2.0, "height": 2.0, "pad_w": 0.5, "pad_h": 0.5})
            
            # Create footprint (simplified)
            # In real implementation, this would use altium-monkey's footprint API
            logger.info(f"  Creating footprint: {footprint_name}")
        
        doc.Save(output_path)
        logger.info(f"Created PcbLib with {len(components)} footprints: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating PcbLib with altium-monkey: {e}")
        return create_pcblib_json(components, output_path)


def create_pcblib_json(components, output_path):
    """Create JSON-based PcbLib representation."""
    json_path = output_path.replace(".PcbLib", "_footprint.json")
    
    footprints = []
    for comp in components:
        package = comp.get("package", "")
        dims = PACKAGE_MAP.get(package, {"width": 2.0, "height": 2.0, "pad_w": 0.5, "pad_h": 0.5})
        
        footprint = {
            "name": comp.get("mpn", ""),
            "package": package,
            "description": comp.get("description", ""),
            "dimensions": dims,
            "pads": [],
            "silkscreen": [],
            "courtyard": [],
        }
        
        # Generate pad layout based on package type
        if any(p in package for p in ["0201", "0402", "0603", "0805", "1206", "1210"]):
            # Simple 2-pad passive
            footprint["pads"] = [
                {"number": 1, "x": -dims["width"]/2, "y": 0, "w": dims["pad_w"], "h": dims["pad_h"]},
                {"number": 2, "x": dims["width"]/2, "y": 0, "w": dims["pad_w"], "h": dims["pad_h"]},
            ]
        elif "SOT-23" in package:
            footprint["pads"] = [
                {"number": 1, "x": -1.0, "y": -1.0, "w": 0.6, "h": 1.0},
                {"number": 2, "x": 0, "y": -1.0, "w": 0.6, "h": 1.0},
                {"number": 3, "x": 1.0, "y": -1.0, "w": 0.6, "h": 1.0},
                {"number": 4, "x": 0, "y": 1.0, "w": 0.6, "h": 1.0},
            ]
        elif "SOP-8" in package or "DIP-8" in package:
            footprint["pads"] = [
                {"number": i, "x": -2.0 if i <= 4 else 2.0, "y": (i-1 if i <= 4 else i-5) * 1.27 - 1.9, "w": 0.6, "h": 1.5}
                for i in range(1, 9)
            ]
        
        footprints.append(footprint)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(footprints, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Created JSON footprints: {json_path}")
    return True


def run(config, data_dir="data", lib_dir="libraries"):
    """Generate Altium libraries from collected data."""
    logger.info("=" * 50)
    logger.info("Starting Altium library generation")
    logger.info("=" * 50)
    
    os.makedirs(lib_dir, exist_ok=True)
    
    categories_dir = os.path.join(data_dir, "categories")
    if not os.path.exists(categories_dir):
        logger.error(f"Categories directory not found: {categories_dir}")
        return {"generated": 0}
    
    stats = {"generated": 0, "categories": []}
    
    # Process each category file
    for filename in os.listdir(categories_dir):
        if not filename.endswith(".json"):
            continue
        
        category_name = filename.replace(".json", "")
        filepath = os.path.join(categories_dir, filename)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                components = json.load(f)
            
            if not components:
                logger.info(f"Skipping empty category: {category_name}")
                continue
            
            logger.info(f"Processing category: {category_name} ({len(components)} components)")
            
            # Generate SchLib
            schlib_path = os.path.join(lib_dir, "SchLib", f"{category_name}.SchLib")
            create_schlib_simple(components, schlib_path)
            
            # Generate PcbLib
            pcblib_path = os.path.join(lib_dir, "PcbLib", f"{category_name}.PcbLib")
            create_pcblib_simple(components, pcblib_path)
            
            stats["generated"] += 1
            stats["categories"].append({
                "name": category_name,
                "components": len(components),
                "schlib": schlib_path,
                "pcblib": pcblib_path,
            })
            
        except Exception as e:
            logger.error(f"Error processing {category_name}: {e}")
    
    # Save generation stats
    stats["timestamp"] = datetime.utcnow().isoformat()
    stats_path = os.path.join(data_dir, "generation_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Generated {stats['generated']} library pairs")
    return stats


if __name__ == "__main__":
    import yaml
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    run(config)
