"""
AI Helper Functions untuk analisis gambar
"""


def analyze_severity(results, img_w, img_h, confidence_threshold=0.4):
    """
    Menganalisis hasil deteksi YOLO lokal untuk menentukan severity.
    
    Args:
        results: Hasil dari YOLO model.predict()
        img_w: Lebar gambar
        img_h: Tinggi gambar
        confidence_threshold: Threshold confidence minimum (default 0.4)
    
    Returns:
        tuple: (severity_status, pothole_count)
    """
    # Ambil boxes dari hasil YOLO
    boxes = results[0].boxes if len(results) > 0 else []
    
    # Filter berdasarkan confidence
    filtered_boxes = []
    for box in boxes:
        conf = float(box.conf[0]) if len(box.conf) > 0 else 0
        if conf > confidence_threshold:
            filtered_boxes.append(box)
    
    count = len(filtered_boxes)

    if count == 0:
        return "AMAN", 0

    serious = False
    img_area = img_w * img_h

    for box in filtered_boxes:
        # YOLO format: xywh atau xyxy
        # box.xywh memberikan [x_center, y_center, width, height]
        if box.xywh is not None and len(box.xywh) > 0:
            xywh = box.xywh[0]  # Ambil tensor pertama
            box_width = float(xywh[2])
            box_height = float(xywh[3])
            box_area = box_width * box_height
            ratio = box_area / img_area
            
            # LOGIKA UKURAN (AREA)
            # Jika area box > 3.5% dari total gambar -> SERIUS
            if ratio > 0.035:
                serious = True
                break

    # LOGIKA JUMLAH
    # Jika ada lebih dari 4 lubang kecil-kecil -> SERIUS (Jalan Hancur)
    # ATAU jika ada 1 lubang besar (serious=True) -> SERIUS
    if count > 4 or serious:
        status = "SERIUS"
    else:
        status = "TIDAK_SERIUS"

    return status, count
