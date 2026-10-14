import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Cotizador de Recetas V2",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).parent
INSUMOS_FILE = BASE / "insumos.json"
RECETAS_FILE = BASE / "recetas.json"

# ---------- Visual ----------
st.markdown("""
<style>
.stApp { background:#F8F6F1; color:#17343D; }
.block-container { max-width:1200px; padding-top:2rem; }
.card {
  background:white; border:1px solid #E8E1D5; border-radius:18px;
  padding:22px; margin:10px 0; box-shadow:0 6px 20px rgba(0,0,0,.035);
}
.hero {
  background:linear-gradient(135deg,#173F49,#245A61);
  color:white; border-radius:22px; padding:30px; margin-bottom:20px;
}
.hero h1 { color:white; margin:0 0 6px 0; }
.badge { padding:5px 10px; border-radius:12px; font-size:.82rem; font-weight:600; }
.green { background:#E6F3EA; color:#21633A; }
.yellow { background:#FFF3D6; color:#805B00; }
.red { background:#FBE7E7; color:#8A2525; }
.metric {
  background:white; border:1px solid #E8E1D5; border-radius:16px;
  padding:16px;
}
.small { color:#6D777A; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
def load_insumos():
    if not INSUMOS_FILE.exists():
        return pd.DataFrame()
    df = pd.DataFrame(json.loads(INSUMOS_FILE.read_text(encoding="utf-8")))
    if not df.empty:
        for c in ["Precio compra","Cantidad compra","Costo por unidad"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def load_recetas():
    if not RECETAS_FILE.exists():
        return []
    try:
        return json.loads(RECETAS_FILE.read_text(encoding="utf-8"))
    except:
        return []

def save_recetas(data):
    RECETAS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

insumos = load_insumos()

# ---------- Helpers ----------
def money(x):
    return f"${x:,.2f} MXN"

def normalize(s):
    s = str(s).lower().strip()
    s = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s)

def find_matches(name, limit=4):
    if insumos.empty:
        return []
    q = normalize(name)
    tokens = [t for t in q.split() if len(t) > 2]
    scored = []
    for _, row in insumos.iterrows():
        n = normalize(row["Ingrediente"])
        score = 0
        if q == n:
            score = 100
        elif q in n or n in q:
            score = 80
        else:
            score = sum(1 for t in tokens if t in n) * 15
        if score:
            scored.append((score, row["Ingrediente"]))
    return [x[1] for x in sorted(scored, reverse=True)[:limit]]

def parse_recipe(text):
    """
    Heurística deliberadamente conservadora.
    Detecta líneas del tipo:
    120 g aceite de oliva
    aceite de oliva 120 ml
    1/2 taza azúcar
    """
    rows = []
    units = r"(g|gr|gramos?|kg|ml|mililitros?|l|litros?|pz|pieza?s?|unidad(?:es)?|tazas?|cdas?|cucharadas?|cditas?|cucharaditas?)"
    num = r"(\d+(?:[.,]\d+)?|\d+\s*/\s*\d+)"
    pat1 = re.compile(r"^\s*" + num + r"\s*" + units + r"\s+(.+?)\s*$", re.I)
    pat2 = re.compile(r"^\s*(.+?)\s+" + num + r"\s*" + units + r"\s*$", re.I)
    for line in text.splitlines():
        line = re.sub(r"^[•\-–—*\d.)]+\s*", "", line).strip()
        if not line:
            continue
        m = pat1.match(line) or pat2.match(line)
        if not m:
            continue
        if pat1.match(line):
            qty, unit, ingredient = m.groups()
        else:
            ingredient, qty, unit = m.groups()
        qty = qty.replace(",", ".").replace(" ", "")
        if "/" in qty:
            a,b = qty.split("/")
            qty = float(a)/float(b)
        else:
            qty = float(qty)
        rows.append({"ingrediente": ingredient.strip(), "cantidad": qty, "unidad": unit.lower()})
    return rows

def compatible_unit(recipe_unit, purchase_unit):
    r = normalize(recipe_unit)
    p = normalize(purchase_unit)
    if r in ("g","gr","gramo","gramos") and "gram" in p:
        return True
    if r == "kg" and "gram" in p:
        return True
    if r in ("ml","mililitro","mililitros") and ("mililit" in p or p in ("ml","mililitros")):
        return True
    if r == "l" and ("mililit" in p or p == "ml"):
        return True
    if r in ("pz","pieza","piezas","unidad","unidades") and ("pieza" in p or "unidad" in p):
        return True
    return r == p

def convert_qty(qty, recipe_unit, purchase_unit):
    r = normalize(recipe_unit)
    p = normalize(purchase_unit)
    if r == "kg" and "gram" in p: return qty * 1000
    if r == "l" and ("mililit" in p or p == "ml"): return qty * 1000
    return qty

def proportional_cost(qty, recipe_unit, row):
    purchase_qty = float(row["Cantidad compra"])
    purchase_price = float(row["Precio compra"])
    if purchase_qty <= 0: return None
    if not compatible_unit(recipe_unit, row["Unidad compra"]):
        return None
    q = convert_qty(qty, recipe_unit, row["Unidad compra"])
    return q / purchase_qty * purchase_price

# ---------- Sidebar ----------
menu = st.sidebar.radio(
    "Navegación",
    ["🏠 Inicio", "➕ Nueva cotización", "📚 Mis recetas", "⚙️ Administración"],
)
st.sidebar.caption("V2 · versión independiente de V1")

# ---------- Home ----------
if menu == "🏠 Inicio":
    st.markdown("""
    <div class="hero">
      <h1>🍳 Cotizador de Recetas</h1>
      <div>Convierte una receta en costo real, precio de venta y rentabilidad.</div>
    </div>
    """, unsafe_allow_html=True)
    a,b = st.columns(2)
    with a:
        st.markdown('<div class="card"><h3>🍳 Nueva cotización</h3><p>Analiza una receta, encuentra sus insumos y calcula el costo proporcional.</p></div>', unsafe_allow_html=True)
        if st.button("Crear cotización", use_container_width=True):
            st.session_state["goto"] = "➕ Nueva cotización"
            st.rerun()
    with b:
        st.markdown('<div class="card"><h3>📚 Mis recetas</h3><p>Guarda, consulta y recostea tus productos.</p></div>', unsafe_allow_html=True)
        if st.button("Ver recetas", use_container_width=True):
            st.session_state["goto"] = "📚 Mis recetas"
            st.rerun()

    st.markdown("### Lo que hace V2")
    c1,c2,c3,c4 = st.columns(4)
    for c, title, txt in zip(
        [c1,c2,c3,c4],
        ["Costeo proporcional","Producción","Presentaciones","Rentabilidad"],
        ["Usa sólo la cantidad realmente consumida.","Equipo, gas, electricidad y mano de obra.","Compara gramajes y empaques.","35% sobre costo o margen real."]
    ):
        with c:
            st.markdown(f'<div class="metric"><b>{title}</b><br><span class="small">{txt}</span></div>', unsafe_allow_html=True)

# ---------- New quote ----------
elif menu == "➕ Nueva cotización":
    st.markdown("## Nueva cotización")
    steps = "1 Producto  →  2 Receta  →  3 Revisión  →  4 Producción  →  5 Venta  →  6 Resultado"
    st.caption(steps)

    name = st.text_input("Nombre del producto", value=st.session_state.get("q_name",""), placeholder="Ej. Salsa Macha de Arándano")
    category = st.selectbox("Categoría", ["Salsas y aderezos","Repostería y panadería","Postres","Platos preparados","Otros"])
    description = st.text_area("Descripción (opcional)", height=70)

    st.markdown("### 2. Ingresa tu receta")
    mode = st.radio("Método", ["📝 Pegar receta","✍️ Captura manual"], horizontal=True)
    recipe_text = ""
    parsed = []

    if mode == "📝 Pegar receta":
        recipe_text = st.text_area(
            "Pega aquí la receta completa",
            height=220,
            placeholder="Ejemplo:\n120 ml aceite de oliva\n80 g chile seco\n30 g ajo\n100 g arándano"
        )
        if st.button("✨ Analizar receta", type="primary"):
            parsed = parse_recipe(recipe_text)
            st.session_state["parsed"] = parsed
            st.session_state["recipe_text"] = recipe_text
    else:
        if "manual_rows" not in st.session_state:
            st.session_state["manual_rows"] = [{"ingrediente":"","cantidad":0.0,"unidad":"g"}]
        rows = st.session_state["manual_rows"]
        for i,row in enumerate(rows):
            c1,c2,c3,c4 = st.columns([4,2,2,1])
            with c1: rows[i]["ingrediente"] = st.text_input("Ingrediente", row["ingrediente"], key=f"mi{i}")
            with c2: rows[i]["cantidad"] = st.number_input("Cantidad", min_value=0.0, value=float(row["cantidad"]), key=f"mq{i}")
            with c3: rows[i]["unidad"] = st.selectbox("Unidad", ["g","ml","kg","l","pieza"], index=["g","ml","kg","l","pieza"].index(row["unidad"]) if row["unidad"] in ["g","ml","kg","l","pieza"] else 0, key=f"mu{i}")
            with c4:
                if st.button("✕", key=f"md{i}"): rows.pop(i); st.rerun()
        if st.button("＋ Agregar ingrediente"):
            rows.append({"ingrediente":"","cantidad":0.0,"unidad":"g"}); st.rerun()
        parsed = [r for r in rows if r["ingrediente"].strip() and r["cantidad"] > 0]

    parsed = st.session_state.get("parsed", parsed)

    if parsed:
        st.markdown("### 3. Revisión de ingredientes")
        st.info(f"Se detectaron **{len(parsed)}** ingredientes. Confirma las coincidencias cuando sea necesario.")
        reviewed = []
        total_ing = 0.0
        for i,item in enumerate(parsed):
            matches = find_matches(item["ingrediente"])
            default = matches[0] if matches else "— Sin coincidencia —"
            options = ["— Sin coincidencia —"] + matches
            if default not in options: default = options[0]
            selected = st.selectbox(
                f'{item["ingrediente"]} · {item["cantidad"]:g} {item["unidad"]}',
                options,
                index=options.index(default),
                key=f"match_{i}"
            )
            cost = None
            purchase_unit = ""
            if selected != "— Sin coincidencia —":
                row = insumos[insumos["Ingrediente"] == selected].iloc[0]
                purchase_unit = row["Unidad compra"]
                cost = proportional_cost(item["cantidad"], item["unidad"], row)
                if cost is None:
                    st.warning(f"Revisa la unidad de **{selected}**: la receta usa {item['unidad']} y el catálogo compra en {purchase_unit}.")
                else:
                    total_ing += cost
                    st.caption(f"🟢 Coincidencia · compra {row['Cantidad compra']:g} {purchase_unit} por {money(row['Precio compra'])} → usado {money(cost)}")
            else:
                st.caption("🔴 Falta asignar un insumo del catálogo.")
            reviewed.append({**item, "catalogo": selected, "costo": cost})
        st.session_state["reviewed"] = reviewed

        st.markdown("### 4. Producción")
        e1,e2,e3 = st.columns(3)
        tmx = e1.number_input("Thermomix · minutos", min_value=0.0, value=0.0, step=5.0)
        horno = e2.number_input("Horno · minutos", min_value=0.0, value=0.0, step=5.0)
        otros = e3.number_input("Otros equipos · costo", min_value=0.0, value=0.0, step=1.0)
        p1,p2,p3 = st.columns(3)
        electricidad = p1.number_input("Electricidad", min_value=0.0, value=0.0, step=1.0)
        gas = p2.number_input("Gas", min_value=0.0, value=0.0, step=1.0)
        mano_obra = p3.number_input("Mano de obra", min_value=0.0, value=0.0, step=1.0)
        merma_pct = st.number_input("Merma (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)

        # Configuración inicial editable: se centralizará en Administración.
        costo_tmx = tmx * 0.333333
        costo_horno = horno * 0.666667
        costo_base = total_ing + costo_tmx + costo_horno + otros + electricidad + gas + mano_obra
        costo_merma = costo_base * merma_pct / 100
        costo_produccion = costo_base + costo_merma

        st.markdown("### 5. Rendimiento y presentación")
        y1,y2 = st.columns(2)
        rendimiento = y1.number_input("Rendimiento total", min_value=0.0, value=1000.0, step=50.0)
        unidad_rend = y2.selectbox("Unidad de rendimiento", ["g","ml","piezas","porciones"])

        presentaciones = [100,120,150,200,250,500]
        if rendimiento > 0 and unidad_rend in ("g","ml"):
            costo_unit = costo_produccion / rendimiento
            data = []
            for pres in presentaciones:
                if pres <= rendimiento:
                    data.append([pres, costo_unit*pres, 0.0, costo_unit*pres])
            df_pres = pd.DataFrame(data, columns=["Presentación","Producto","Empaque","Costo total"])
            st.dataframe(df_pres, use_container_width=True, hide_index=True)
            st.caption(f"Costo base por {unidad_rend}: {money(costo_unit)}")

        st.markdown("### 6. Precio de venta")
        m1,m2 = st.columns(2)
        metodo = m1.radio("Método", ["35% sobre costo","35% margen real"], horizontal=True)
        precio_manual = m2.number_input("Precio final opcional", min_value=0.0, value=0.0, step=5.0)
        if metodo == "35% sobre costo":
            precio = costo_produccion * 1.35
        else:
            precio = costo_produccion / .65 if costo_produccion else 0
        if precio_manual > 0:
            precio = precio_manual
        ganancia = precio - costo_produccion
        margen = ganancia/precio*100 if precio else 0

        a,b,c,d = st.columns(4)
        a.metric("Insumos", money(total_ing))
        b.metric("Costo producción", money(costo_produccion))
        c.metric("Precio", money(precio))
        d.metric("Ganancia", money(ganancia))

        st.markdown("### Resultado")
        st.success(f"**Precio sugerido: {money(precio)} · Ganancia: {money(ganancia)} · Margen: {margen:.1f}%**")

        if st.button("💾 Guardar receta", type="primary"):
            recetas = load_recetas()
            recetas.append({
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "nombre": name.strip(),
                "categoria": category,
                "descripcion": description,
                "ingredientes": reviewed,
                "costo_ingredientes": round(total_ing,2),
                "costo_produccion": round(costo_produccion,2),
                "rendimiento": rendimiento,
                "unidad_rendimiento": unidad_rend,
                "precio": round(precio,2),
                "ganancia": round(ganancia,2),
                "margen": round(margen,2),
                "fecha": datetime.now().isoformat(timespec="seconds")
            })
            save_recetas(recetas)
            st.success("Receta guardada correctamente.")

# ---------- Recipes ----------
elif menu == "📚 Mis recetas":
    st.markdown("## Mis recetas")
    recetas = load_recetas()
    if not recetas:
        st.info("Todavía no hay recetas guardadas en V2.")
    else:
        q = st.text_input("Buscar por nombre o categoría")
        filtered = [r for r in recetas if q.lower() in (r.get("nombre","")+" "+r.get("categoria","")).lower()]
        for r in filtered:
            with st.container(border=True):
                c1,c2,c3 = st.columns([4,2,2])
                c1.subheader(r.get("nombre","Sin nombre"))
                c1.caption(r.get("categoria",""))
                c2.metric("Costo", money(r.get("costo_produccion",0)))
                c3.metric("Precio", money(r.get("precio",0)))
                with st.expander("Ver detalle"):
                    st.write(f"Rendimiento: {r.get('rendimiento')} {r.get('unidad_rendimiento')}")
                    st.write(f"Ganancia: {money(r.get('ganancia',0))} · Margen: {r.get('margen',0):.1f}%")
                    if r.get("ingredientes"):
                        st.dataframe(pd.DataFrame(r["ingredientes"]), use_container_width=True, hide_index=True)

# ---------- Admin ----------
elif menu == "⚙️ Administración":
    st.markdown("## Administración")
    st.warning("Esta primera construcción de V2 deja esta sección preparada para conectar la administración privada y la persistencia robusta.")
    st.markdown("### Catálogo de insumos")
    if insumos.empty:
        st.error("No se encontró insumos.json")
    else:
        q = st.text_input("Buscar ingrediente")
        view = insumos[insumos["Ingrediente"].str.contains(q, case=False, na=False)] if q else insumos
        st.dataframe(
            view[["Ingrediente","Precio compra","Cantidad compra","Unidad compra","Costo por unidad","Compra / proveedor"]],
            use_container_width=True, height=500, hide_index=True
        )
        st.caption(f"{len(insumos)} insumos cargados desde el Excel base.")

st.sidebar.divider()
st.sidebar.caption("V2 independiente · V1 no modificada")
