from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from src.services.api_client import PortalAPIClient

portal_bp = Blueprint("portal", __name__)


def _get_carrito(slug: str) -> list:
    carritos = session.get("carritos", {})
    return list(carritos.get(slug, []))


def _save_carrito(slug: str, items: list):
    carritos = dict(session.get("carritos", {}))
    carritos[slug] = items
    session["carritos"] = carritos
    session.modified = True


def _cargar_contexto_portal(slug: str):
    """Obtiene la configuración pública e identidad de la empresa desde PYMES_BE."""
    data, err = PortalAPIClient.get(f"/portal/publico/{slug}")
    if err or not data or not data.get("exito"):
        return None, err or "El portal solicitado no está disponible."
    return data, None


# =========================================================================
# 1. DIRECTORIO MULTIEMPRESA / PORTADA GLOBAL DEL PORTAL DE CLIENTES
# =========================================================================
@portal_bp.route("/")
def directorio():
    default_slug = current_app.config.get("DEFAULT_EMPRESA_SLUG", "").strip()
    if default_slug:
        return redirect(url_for("portal.inicio_empresa", slug=default_slug))

    data, _ = PortalAPIClient.get("/portal/publico/empresas")
    portales = data.get("portales", []) if isinstance(data, dict) else []
    return render_template("directorio.html", portales=portales)


# =========================================================================
# 2. SECCIONES PÚBLICAS DEL PORTAL POR EMPRESA (/e/<slug>/...)
# =========================================================================
@portal_bp.route("/e/<slug>")
def inicio_empresa(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    return render_template(
        "inicio.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        categorias=ctx.get("categorias", []),
        productos_destacados=ctx.get("productos_destacados", []),
        servicios=ctx.get("servicios", []),
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/catalogo")
def catalogo(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    q = request.args.get("q", "").strip()
    id_categoria = request.args.get("id_categoria", "").strip()
    res, _ = PortalAPIClient.get(
        f"/portal/publico/{slug}/productos",
        params={"q": q, "id_categoria": id_categoria},
    )
    productos = res.get("productos", []) if isinstance(res, dict) else []
    categorias = res.get("categorias", ctx.get("categorias", [])) if isinstance(res, dict) else []

    return render_template(
        "catalogo.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        productos=productos,
        categorias=categorias,
        q=q,
        id_categoria=id_categoria,
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/producto/<int:producto_id>")
def detalle_producto(slug, producto_id):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    res, err_p = PortalAPIClient.get(f"/portal/publico/{slug}/productos/{producto_id}")
    if err_p or not res or not res.get("producto"):
        flash(err_p or "El producto solicitado no se encuentra disponible en esta empresa.", "warning")
        return redirect(url_for("portal.catalogo", slug=slug))

    return render_template(
        "detalle_producto.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        producto=res["producto"],
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/servicios")
def servicios(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    res, _ = PortalAPIClient.get(f"/portal/publico/{slug}/servicios")
    lista_servicios = res.get("servicios", []) if isinstance(res, dict) else []

    return render_template(
        "servicios.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        servicios=lista_servicios,
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/reservar", methods=["GET", "POST"])
@portal_bp.route("/e/<slug>/reservar/<int:servicio_id>", methods=["GET", "POST"])
def reservar(slug, servicio_id=None):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    if not session.get("cliente_access_token"):
        flash("Inicia sesión o regístrate como cliente para agendar tu cita o servicio.", "info")
        return redirect(url_for("portal.login", slug=slug))

    res_srv, _ = PortalAPIClient.get(f"/portal/publico/{slug}/servicios")
    lista_servicios = res_srv.get("servicios", []) if isinstance(res_srv, dict) else []

    id_sel = servicio_id or request.args.get("id_servicio", type=int) or (lista_servicios[0]["id"] if lista_servicios else None)
    fecha_sel = request.args.get("fecha") or datetime.now().strftime("%Y-%m-%d")

    horarios = []
    if id_sel:
        res_h, _ = PortalAPIClient.get(
            f"/portal/publico/{slug}/servicios/{id_sel}/horarios",
            params={"fecha": fecha_sel},
        )
        if isinstance(res_h, dict):
            horarios = res_h.get("horarios", [])

    if request.method == "POST":
        payload = {
            "id_servicio": int(request.form.get("id_servicio") or id_sel or 0),
            "fecha_reserva": request.form.get("fecha_reserva", "").strip(),
            "hora_inicio": request.form.get("hora_inicio", "").strip(),
            "notas_cliente": request.form.get("notas_cliente", "").strip(),
        }
        res_post, err_post = PortalAPIClient.post(f"/portal/cliente/{slug}/reservas", data=payload)
        if err_post:
            flash(err_post, "danger")
        else:
            flash(res_post.get("mensaje", "¡Reserva agendada exitosamente!"), "success")
            return redirect(url_for("portal.mi_cuenta", slug=slug) + "#reservas")

    return render_template(
        "reservar.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        servicios=lista_servicios,
        servicio_seleccionado=id_sel,
        fecha_seleccionada=fecha_sel,
        horarios=horarios,
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


# =========================================================================
# 3. CARRITO DE COMPRAS Y CHECKOUT VALIDADO EN SERVIDOR
# =========================================================================
@portal_bp.route("/e/<slug>/carrito")
def carrito(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    items_sesion = _get_carrito(slug)
    resumen = {"items": [], "subtotal": 0.0, "costo_envio": 0.0, "total": 0.0}
    if items_sesion:
        val_res, val_err = PortalAPIClient.post(
            f"/portal/publico/{slug}/carrito/validar",
            data={"items": items_sesion, "modalidad_entrega": "Domicilio"},
        )
        if val_err:
            flash(f"Aviso en tu carrito: {val_err}", "warning")
        elif isinstance(val_res, dict):
            resumen = val_res

    return render_template(
        "carrito.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        resumen=resumen,
        carrito_count=sum(i.get("cantidad", 0) for i in items_sesion),
    )


@portal_bp.route("/e/<slug>/carrito/agregar", methods=["POST"])
def carrito_agregar(slug):
    id_prod = request.form.get("id_producto", type=int)
    cantidad = max(1, request.form.get("cantidad", 1, type=int) or 1)
    if not id_prod:
        return redirect(url_for("portal.catalogo", slug=slug))

    items = _get_carrito(slug)
    encontrado = False
    for it in items:
        if int(it.get("id_producto", 0)) == id_prod:
            it["cantidad"] = int(it.get("cantidad", 0)) + cantidad
            encontrado = True
            break
    if not encontrado:
        items.append({"id_producto": id_prod, "cantidad": cantidad})

    # Validar disponibilidad en el backend antes de confirmar la adición
    _, err = PortalAPIClient.post(f"/portal/publico/{slug}/carrito/validar", data={"items": items})
    if err:
        flash(err, "danger")
        return redirect(request.referrer or url_for("portal.catalogo", slug=slug))

    _save_carrito(slug, items)
    flash("Producto agregado al carrito de compras.", "success")
    return redirect(request.referrer or url_for("portal.carrito", slug=slug))


@portal_bp.route("/e/<slug>/carrito/actualizar", methods=["POST"])
def carrito_actualizar(slug):
    id_prod = request.form.get("id_producto", type=int)
    cantidad = request.form.get("cantidad", 0, type=int) or 0
    items = _get_carrito(slug)
    nuevos = []
    for it in items:
        if int(it.get("id_producto", 0)) == id_prod:
            if cantidad > 0:
                nuevos.append({"id_producto": id_prod, "cantidad": cantidad})
        else:
            nuevos.append(it)

    if nuevos:
        _, err = PortalAPIClient.post(f"/portal/publico/{slug}/carrito/validar", data={"items": nuevos})
        if err:
            flash(err, "danger")
            return redirect(url_for("portal.carrito", slug=slug))

    _save_carrito(slug, nuevos)
    flash("Carrito actualizado.", "info")
    return redirect(url_for("portal.carrito", slug=slug))


@portal_bp.route("/e/<slug>/carrito/vaciar", methods=["POST"])
def carrito_vaciar(slug):
    _save_carrito(slug, [])
    flash("Se ha vaciado tu carrito de compras.", "info")
    return redirect(url_for("portal.catalogo", slug=slug))


@portal_bp.route("/e/<slug>/checkout", methods=["GET", "POST"])
def checkout(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        flash(err, "warning")
        return redirect(url_for("portal.directorio"))

    if not session.get("cliente_access_token"):
        flash("Por favor inicia sesión o crea tu cuenta para confirmar el pedido.", "info")
        return redirect(url_for("portal.login", slug=slug))

    items_sesion = _get_carrito(slug)
    if not items_sesion:
        flash("Tu carrito está vacío. Agrega productos antes de finalizar el pedido.", "warning")
        return redirect(url_for("portal.catalogo", slug=slug))

    modalidad_sel = request.args.get("modalidad") or request.form.get("modalidad_entrega") or "Domicilio"
    val_res, val_err = PortalAPIClient.post(
        f"/portal/publico/{slug}/carrito/validar",
        data={"items": items_sesion, "modalidad_entrega": modalidad_sel},
    )
    if val_err or not val_res:
        flash(val_err or "No fue posible validar el carrito.", "danger")
        return redirect(url_for("portal.carrito", slug=slug))

    perfil_res, _ = PortalAPIClient.get("/portal/cliente/perfil")
    cliente_info = perfil_res.get("cliente", session.get("cliente_cuenta", {})) if isinstance(perfil_res, dict) else {}

    if request.method == "POST":
        payload = {
            "items": items_sesion,
            "modalidad_entrega": request.form.get("modalidad_entrega", "Domicilio"),
            "direccion_entrega": request.form.get("direccion_entrega", "").strip(),
            "ciudad_entrega": request.form.get("ciudad_entrega", "").strip(),
            "telefono_contacto": request.form.get("telefono_contacto", "").strip(),
            "id_metodo_pago": request.form.get("id_metodo_pago"),
            "notas_cliente": request.form.get("notas_cliente", "").strip(),
        }
        ped_res, ped_err = PortalAPIClient.post(f"/portal/cliente/{slug}/pedidos", data=payload)
        if ped_err or not ped_res:
            flash(ped_err or "Error al confirmar el pedido.", "danger")
        else:
            _save_carrito(slug, [])
            pedido_creado = ped_res.get("pedido", {})
            flash(ped_res.get("mensaje", "¡Pedido confirmado exitosamente!"), "success")
            return redirect(url_for("portal.detalle_pedido_cliente", slug=slug, pedido_id=pedido_creado.get("id")))

    return render_template(
        "checkout.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        metodos_pago=ctx.get("metodos_pago", []),
        resumen=val_res,
        cliente=cliente_info,
        carrito_count=sum(i.get("cantidad", 0) for i in items_sesion),
    )


# =========================================================================
# 4. AUTENTICACIÓN Y ÁREA PRIVADA DEL CLIENTE (/e/<slug>/mi-cuenta)
# =========================================================================
@portal_bp.route("/e/<slug>/login", methods=["GET", "POST"])
def login(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    if request.method == "POST":
        payload = {
            "email": request.form.get("email", "").strip(),
            "password": request.form.get("password", ""),
            "slug": slug,
        }
        res, err_log = PortalAPIClient.post("/portal/cliente/auth/login", data=payload)
        if err_log or not res or not res.get("exito"):
            flash(err_log or "Credenciales inválidas.", "danger")
        else:
            session["cliente_access_token"] = res.get("access_token")
            session["cliente_cuenta"] = res.get("cliente", {})
            flash(f"¡Bienvenido, {res.get('cliente', {}).get('nombre', '')}!", "success")
            return redirect(url_for("portal.mi_cuenta", slug=slug))

    return render_template(
        "login.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/registro", methods=["GET", "POST"])
def registro(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    if request.method == "POST":
        payload = {
            "tipo_documento": request.form.get("tipo_documento", "CC"),
            "documento": request.form.get("documento", "").strip(),
            "nombre": request.form.get("nombre", "").strip(),
            "apellido": request.form.get("apellido", "").strip(),
            "email": request.form.get("email", "").strip(),
            "telefono": request.form.get("telefono", "").strip(),
            "direccion": request.form.get("direccion", "").strip(),
            "ciudad": request.form.get("ciudad", "").strip(),
            "password": request.form.get("password", ""),
            "slug": slug,
        }
        res, err_reg = PortalAPIClient.post("/portal/cliente/auth/register", data=payload)
        if err_reg or not res or not res.get("exito"):
            flash(err_reg or "No se pudo completar el registro.", "danger")
        else:
            session["cliente_access_token"] = res.get("access_token")
            session["cliente_cuenta"] = res.get("cliente", {})
            flash("¡Tu cuenta de cliente ha sido creada exitosamente!", "success")
            return redirect(url_for("portal.mi_cuenta", slug=slug))

    return render_template(
        "registro.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/recuperar-password", methods=["GET", "POST"])
def recuperar_password(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    paso_codigo = False
    email_ingresado = request.args.get("email", "").strip()

    if request.method == "POST":
        email_ingresado = request.form.get("email", "").strip()
        res, err_rec = PortalAPIClient.post(
            "/portal/cliente/auth/recuperar-solicitar",
            data={"email": email_ingresado},
        )
        if err_rec:
            flash(err_rec, "danger")
        else:
            flash(res.get("mensaje", "Instrucciones enviadas a tu correo."), "info")
            paso_codigo = True

    return render_template(
        "recuperar_password.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        paso_codigo=paso_codigo,
        email=email_ingresado,
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/recuperar-password/confirmar", methods=["POST"])
def recuperar_password_confirmar(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    email = request.form.get("email", "").strip()
    codigo = request.form.get("codigo", "").strip()
    password_nueva = request.form.get("password_nueva", "")
    res, err_conf = PortalAPIClient.post(
        "/portal/cliente/auth/recuperar-confirmar",
        data={"email": email, "codigo": codigo, "password_nueva": password_nueva},
    )
    if err_conf:
        flash(err_conf, "danger")
        return render_template(
            "recuperar_password.html",
            slug=slug,
            empresa=ctx.get("empresa", {}),
            portal=ctx.get("portal", {}),
            paso_codigo=True,
            email=email,
            carrito_count=0,
        )

    flash(res.get("mensaje", "Contraseña restablecida exitosamente."), "success")
    return redirect(url_for("portal.login", slug=slug))


@portal_bp.route("/e/<slug>/logout")
def logout(slug):
    session.pop("cliente_access_token", None)
    session.pop("cliente_cuenta", None)
    flash("Has cerrado sesión en el portal de clientes.", "info")
    return redirect(url_for("portal.inicio_empresa", slug=slug))


@portal_bp.route("/e/<slug>/mi-cuenta")
def mi_cuenta(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    if not session.get("cliente_access_token"):
        return redirect(url_for("portal.login", slug=slug))

    perfil_res, _ = PortalAPIClient.get("/portal/cliente/perfil")
    pedidos_res, _ = PortalAPIClient.get(f"/portal/cliente/{slug}/pedidos")
    reservas_res, _ = PortalAPIClient.get(f"/portal/cliente/{slug}/reservas")
    facturas_res, _ = PortalAPIClient.get(f"/portal/cliente/{slug}/facturas")
    solicitudes_res, _ = PortalAPIClient.get(f"/portal/cliente/{slug}/solicitudes")
    notifs_res, _ = PortalAPIClient.get(f"/portal/cliente/{slug}/notificaciones")

    return render_template(
        "mi_cuenta.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        cliente=(perfil_res or {}).get("cliente", session.get("cliente_cuenta", {})),
        pedidos=(pedidos_res or {}).get("pedidos", []),
        reservas=(reservas_res or {}).get("reservas", []),
        facturas=(facturas_res or {}).get("facturas", []),
        solicitudes=(solicitudes_res or {}).get("solicitudes", []),
        notificaciones=(notifs_res or {}).get("notificaciones", []),
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/mi-cuenta/perfil", methods=["POST"])
def actualizar_perfil(slug):
    payload = {
        "nombre": request.form.get("nombre", "").strip(),
        "apellido": request.form.get("apellido", "").strip(),
        "telefono": request.form.get("telefono", "").strip(),
        "direccion_principal": request.form.get("direccion_principal", "").strip(),
        "ciudad": request.form.get("ciudad", "").strip(),
    }
    res, err = PortalAPIClient.put("/portal/cliente/perfil", data=payload)
    if err:
        flash(err, "danger")
    else:
        session["cliente_cuenta"] = res.get("cliente", session.get("cliente_cuenta", {}))
        flash("Tus datos personales han sido actualizados.", "success")
    return redirect(url_for("portal.mi_cuenta", slug=slug))


@portal_bp.route("/e/<slug>/mi-cuenta/direcciones", methods=["POST"])
def agregar_direccion(slug):
    payload = {
        "alias": request.form.get("alias", "Casa").strip(),
        "direccion": request.form.get("direccion", "").strip(),
        "ciudad": request.form.get("ciudad", "").strip(),
        "telefono_contacto": request.form.get("telefono_contacto", "").strip(),
        "es_principal": request.form.get("es_principal") == "on",
    }
    _, err = PortalAPIClient.post("/portal/cliente/direcciones", data=payload)
    if err:
        flash(err, "danger")
    else:
        flash("Nueva dirección guardada en tu libreta.", "success")
    return redirect(url_for("portal.mi_cuenta", slug=slug) + "#direcciones")


@portal_bp.route("/e/<slug>/mi-cuenta/vincular/solicitar", methods=["POST"])
def solicitar_vinculacion(slug):
    res, err = PortalAPIClient.post(f"/portal/cliente/{slug}/vincular-solicitar", data={})
    if err:
        flash(err, "danger")
    else:
        flash(res.get("mensaje", "Código OTP enviado."), "info")
    return redirect(url_for("portal.mi_cuenta", slug=slug) + "#facturas")


@portal_bp.route("/e/<slug>/mi-cuenta/vincular/confirmar", methods=["POST"])
def confirmar_vinculacion(slug):
    codigo = request.form.get("codigo", "").strip()
    res, err = PortalAPIClient.post(
        f"/portal/cliente/{slug}/vincular-confirmar",
        data={"codigo": codigo},
    )
    if err:
        flash(err, "danger")
    else:
        flash(res.get("mensaje", "Vinculación comercial verificada."), "success")
    return redirect(url_for("portal.mi_cuenta", slug=slug) + "#facturas")


@portal_bp.route("/e/<slug>/mi-cuenta/pedidos/<int:pedido_id>")
def detalle_pedido_cliente(slug, pedido_id):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    res, err_p = PortalAPIClient.get(f"/portal/cliente/{slug}/pedidos/{pedido_id}")
    if err_p or not res or not res.get("pedido"):
        flash(err_p or "Pedido no encontrado.", "danger")
        return redirect(url_for("portal.mi_cuenta", slug=slug))

    return render_template(
        "detalle_pedido.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        pedido=res["pedido"],
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )


@portal_bp.route("/e/<slug>/mi-cuenta/pedidos/<int:pedido_id>/cancelar", methods=["POST"])
def cancelar_pedido_cliente(slug, pedido_id):
    motivo = request.form.get("motivo", "Cancelado por el cliente desde el portal.")
    res, err = PortalAPIClient.post(
        f"/portal/cliente/{slug}/pedidos/{pedido_id}/cancelar",
        data={"motivo": motivo},
    )
    if err:
        flash(err, "danger")
    else:
        flash(res.get("mensaje", "Pedido cancelado."), "info")
    return redirect(url_for("portal.detalle_pedido_cliente", slug=slug, pedido_id=pedido_id))


@portal_bp.route("/e/<slug>/mi-cuenta/pedidos/<int:pedido_id>/pagar", methods=["POST"])
def pagar_pedido_cliente(slug, pedido_id):
    res, err = PortalAPIClient.post(
        f"/portal/cliente/{slug}/pedidos/{pedido_id}/cobros",
        data={"canal": "link"},
    )
    if err:
        flash(err, "danger")
    else:
        flash("Transacción de pago en línea iniciada.", "info")
    return redirect(url_for("portal.detalle_pedido_cliente", slug=slug, pedido_id=pedido_id))


@portal_bp.route("/e/<slug>/mi-cuenta/pedidos/<int:pedido_id>/simular/<int:cobro_id>", methods=["POST"])
def simular_pago_pedido_cliente(slug, pedido_id, cobro_id):
    resultado = request.form.get("resultado", "APROBADA")
    res, err = PortalAPIClient.post(
        f"/portal/cliente/{slug}/pedidos/{pedido_id}/cobros/{cobro_id}/simular",
        data={"resultado": resultado},
    )
    if err:
        flash(err, "danger")
    else:
        flash(f"Pago simulado con resultado: {resultado}", "success" if resultado == "APROBADA" else "warning")
    return redirect(url_for("portal.detalle_pedido_cliente", slug=slug, pedido_id=pedido_id))


@portal_bp.route("/e/<slug>/mi-cuenta/reservas/<int:reserva_id>/cancelar", methods=["POST"])
def cancelar_reserva_cliente(slug, reserva_id):
    res, err = PortalAPIClient.post(f"/portal/cliente/{slug}/reservas/{reserva_id}/cancelar", data={})
    if err:
        flash(err, "danger")
    else:
        flash(res.get("mensaje", "Reserva cancelada."), "info")
    return redirect(url_for("portal.mi_cuenta", slug=slug) + "#reservas")


@portal_bp.route("/e/<slug>/contacto", methods=["GET", "POST"])
def contacto(slug):
    ctx, err = _cargar_contexto_portal(slug)
    if err:
        return redirect(url_for("portal.directorio"))

    if request.method == "POST":
        payload = {
            "tipo": request.form.get("tipo", "Consulta"),
            "asunto": request.form.get("asunto", "").strip(),
            "mensaje": request.form.get("mensaje", "").strip(),
            "nombre_contacto": request.form.get("nombre_contacto", "").strip(),
            "email_contacto": request.form.get("email_contacto", "").strip(),
            "telefono_contacto": request.form.get("telefono_contacto", "").strip(),
        }
        endpoint = f"/portal/cliente/{slug}/solicitudes" if session.get("cliente_access_token") else f"/portal/publico/{slug}/contacto"
        res, err_sol = PortalAPIClient.post(endpoint, data=payload)
        if err_sol:
            flash(err_sol, "danger")
        else:
            flash(res.get("mensaje", "Tu mensaje ha sido enviado a la empresa."), "success")
            return redirect(url_for("portal.contacto", slug=slug))

    return render_template(
        "contacto.html",
        slug=slug,
        empresa=ctx.get("empresa", {}),
        portal=ctx.get("portal", {}),
        carrito_count=sum(i.get("cantidad", 0) for i in _get_carrito(slug)),
    )
