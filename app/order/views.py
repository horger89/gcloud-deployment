from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from .models import Order, OrderItem
from product.models import Product
from .serializers import OrderSerializer
from .filters import OrdersFilter
from rest_framework.pagination import PageNumberPagination
import stripe
import os
from utils.helpers import get_current_host
from django.contrib.auth.models import User
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


# Create your views here.


@swagger_auto_schema(
    method='POST',
    request_body=openapi.Schema(
        type='object',
        properties={
            'street': openapi.Schema(type='string'),
            'city': openapi.Schema(type='string'),
            'state': openapi.Schema(type='string'),
            'zip_code': openapi.Schema(type='string'),
            'phone_no': openapi.Schema(type='string'),
            'country': openapi.Schema(type='string'),
            'orderItems': openapi.Schema(
                type='array',
                items=openapi.Schema(
                    type='object',
                    properties={
                        'product': openapi.Schema(type='integer'),
                        'quantity': openapi.Schema(type='integer'),
                        'price': openapi.Schema(type='integer'),
                    }
                )
            )
        },
        required=['street', 'city', 'state', 'zip_code', 'phone_no',
                  'country', 'orderItems']
    )
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def new_order(request):
    """Create New Order"""
    user = request.user
    data = request.data

    order_items = data["orderItems"]

    if order_items and len(order_items) == 0:
        return Response({
            "error": "No order Items. Please add at least one product"
            },
                        status=status.HTTP_400_BAD_REQUEST)

    else:
        # Create order
        total_amount = sum(
           item["price"] * item["quantity"] for item in order_items
        )

        order = Order.objects.create(
            user=user,
            street=data["street"],
            city=data["city"],
            state=data["state"],
            zip_code=data["zip_code"],
            phone_no=data["phone_no"],
            country=data["country"],
            total_amount=total_amount,

        )

        # Create order items and set order to order items
        for i in order_items:
            product = Product.objects.get(id=i["product"])

            item = OrderItem.objects.create(
                product=product,
                order=order,
                name=product.name,
                quantity=i["quantity"],
                price=i["price"]
            )

        # Update product stock
        product.stock -= item.quantity
        product.save()

        serializer = OrderSerializer(order, many=False)

        return Response(serializer.data)


@swagger_auto_schema(method='GET')
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_orders(request):
    """Get All Orders
       Example of filter use:
       /api/orders/?user=2&page=4"""
    filterset = OrdersFilter(request.GET,
                             queryset=Order.objects.all().order_by("id")
                             )

    count = filterset.queryset.count()

    # Pagination
    resPerPage = 10
    paginator = PageNumberPagination()
    paginator.page_size = resPerPage

    queryset = paginator.paginate_queryset(filterset.qs, request)

    serializer = OrderSerializer(queryset, many=True)

    return Response({
        "count": count,
        "resPerPage": resPerPage,
        "orders": serializer.data
        })


@swagger_auto_schema(method='GET')
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_order(request, pk):
    """Get A Single Order by it's ID"""
    order = get_object_or_404(Order, id=pk)

    serializer = OrderSerializer(order, many=False)

    return Response({"order": serializer.data})


@swagger_auto_schema(
    method="PUT",
    request_body=openapi.Schema(
        type='object',
        properties={
             "status": openapi.Schema(type='string'),
        },
        required=["status"]
    )
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsAdminUser])
def process_order(request, pk):
    """Process The Order by it's Order ID"""
    order = get_object_or_404(Order, id=pk)

    order.status = request.data["status"]

    order.save()

    serializer = OrderSerializer(order, many=False)

    return Response({"order": serializer.data})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_order(request, pk):
    """Delete Order by ID"""
    order = get_object_or_404(Order, id=pk)

    order.delete()

    return Response({"details": "Order cancelled."})


stripe.api_key = os.environ.get("STRIPE_PRIVATE_KEY")


@swagger_auto_schema(
    method='POST',
    request_body=openapi.Schema(
        type='object',
        properties={
            'street': openapi.Schema(type='string'),
            'city': openapi.Schema(type='string'),
            'state': openapi.Schema(type='string'),
            'zip_code': openapi.Schema(type='string'),
            'phone_no': openapi.Schema(type='string'),
            'country': openapi.Schema(type='string'),
            'orderItems': openapi.Schema(
                type='array',
                items=openapi.Schema(
                    type='object',
                    properties={
                        'product': openapi.Schema(type='integer'),
                        'name': openapi.Schema(type='string'),
                        'image': openapi.Schema(type='string'),
                        'quantity': openapi.Schema(type='integer'),
                        'price': openapi.Schema(type='integer'),
                    }
                )
            )
        },
        required=['street', 'city', 'state', 'zip_code', 'phone_no',
                  'country', 'orderItems']
    )
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create a Stripe Checkout Session"""
    YOUR_DOMAIN = get_current_host(request)

    user = request.user
    data = request.data

    order_items = data["orderItems"]

    shipping_details = {
        "street": data["street"],
        "city": data["city"],
        "state": data["state"],
        "zip_code": data["zip_code"],
        "phone_no": data["phone_no"],
        "country": data["country"],
        "user": user.id
    }

    checkout_order_items = []
    for item in order_items:
        checkout_order_items.append({
            "price_data": {
                "currency": "USD",
                "product_data": {
                    "name": item["name"],
                    "images": [item["image"]],
                    "metadata": {"product_id": item["product"]}
                },
                "unit_amount": item["price"] * 100
            },
            "quantity": item["quantity"]
        })

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        metadata=shipping_details,
        line_items=checkout_order_items,
        customer_email=user.email,
        mode="payment",
        success_url=YOUR_DOMAIN,
        cancel_url=YOUR_DOMAIN
    )

    return Response({"session": session})


@api_view(["POST"])
def stripe_webhook(request):
    """Stripe WebHook for Completing Checkout"""
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
            )

    except ValueError:
        return Response({"error": "Invalid Payload"},
                        status=status.HTTP_400_BAD_REQUEST
                        )
    except stripe.error.SignatureVerificationError:
        return Response({"error": "Invalid Signature"},
                        status=status.HTTP_400_BAD_REQUEST
                        )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        line_items = stripe.checkout.Session.list_line_items(session["id"])

        price = session["amount_total"] / 100

        order = Order.objects.create(
            user=get_object_or_404(User, id=session.metadata.user),
            street=session.metadata.street,
            city=session.metadata.city,
            state=session.metadata.state,
            zip_code=session.metadata.zip_code,
            phone_no=session.metadata.phone_no,
            country=session.metadata.country,
            total_amount=price,
            payment_status="PAID"
        )

        for item in line_items["data"]:

            print("item", item)

            line_product = stripe.Product.retrieve(item.price.product)
            product_id = line_product.metadata.product_id

            product = Product.objects.get(id=product_id)

            item = OrderItem.objects.create(
                product=product,
                order=order,
                name=product.name,
                quantity=item.quantity,
                price=item.price.unit_amount / 100,
                image=line_product.images[0]
            )

            product.stock -= item.quantity
            product.save()

        return Response({"details": "Payment succesful"})
