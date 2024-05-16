from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from .models import Product, ProductImages, Review
from rest_framework.response import Response
from .serializers import ProductSerializer, ProductImagesSerializer
from .filters import ProductsFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Create your views here.


@swagger_auto_schema(method='GET')
@api_view(['GET'])
def get_products(request):
    """Get All Products"""
    filterset = ProductsFilter(
        request.GET, queryset=Product.objects.all().order_by("id")
        )

    count = filterset.qs.count()

    # Pagination
    resPerPage = 5
    paginator = PageNumberPagination()
    paginator.page_size = resPerPage
    queryset = paginator.paginate_queryset(filterset.qs, request)

    serializer = ProductSerializer(queryset, many=True)

    return Response({"products": serializer.data,
                     "count": count,
                     "resPerPage": resPerPage
                     })


@swagger_auto_schema(method='GET')
@api_view(['GET'])
def get_product(request, pk):
    """Get A Single Product by it's ID"""
    product = get_object_or_404(Product, id=pk)

    serializer = ProductSerializer(product, many=False)

    return Response({"product": serializer.data})


@swagger_auto_schema(
    method='POST',
    request_body=openapi.Schema(
        type='object',
        properties={
            "name": openapi.Schema(type='string'),
            "description": openapi.Schema(type='string'),
            "price": openapi.Schema(type='string'),
            "brand": openapi.Schema(type='string'),
            "category": openapi.Schema(type='string'),
            "stock": openapi.Schema(type='integer')
        },
        required=["name", "description", "price", "brand", "category", "stock"]
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def new_product(request):
    """Create New Product"""
    data = request.data

    serializer = ProductSerializer(data=data)

    if serializer.is_valid():

        product = Product.objects.create(**data, user=request.user)

        res = ProductSerializer(product, many=False)

        return Response({"product": res.data})

    else:

        return Response(serializer.errors)


@swagger_auto_schema(
    method='POST',
    request_body=openapi.Schema(
        type='object',
        properties={
            'product': openapi.Schema(type='integer'),
            'images': openapi.Schema(
                type='array',  # Array of items
                items=openapi.Schema(  # Define the schema for each item
                    type='string',  # Specify the overall type as string
                    oneOf=[  # Allow one of the following formats
                        openapi.Schema(type='string', format='binary'),
                        openapi.Schema(type='string', format='uri')
                    ]
                ),
                description="""
                An array containing base64 encoded image data.
                """
            )
        },
        required=['product', 'images']
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_product_images(request):
    """Upload Images to AWS bucket"""
    data = request.data
    files = request.FILES.getlist("images")

    images = []
    for f in files:
        image = ProductImages.objects.create(product=Product(data['product']),
                                             image=f
                                             )
        images.append(image)

    serializer = ProductImagesSerializer(images, many=True)

    return Response(serializer.data)


@swagger_auto_schema(
    method="PUT",
    request_body=openapi.Schema(
        type='object',
        properties={
            "name": openapi.Schema(type='string'),
            "description": openapi.Schema(type='string'),
            "price": openapi.Schema(type='string'),
            "brand": openapi.Schema(type='string'),
            "category": openapi.Schema(type='string'),
            "stock": openapi.Schema(type='string'),
            "ratings": openapi.Schema(type='string')  
        }
    )
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_product(request, pk):
    """Update Product Details"""
    product = get_object_or_404(Product, id=pk)

    # Check if the user is the owner of the product
    if product.user != request.user:
        return Response({
            "error": "Only the owner of the product can update this"
            },
                        status=status.HTTP_403_FORBIDDEN
                        )

    product.name = request.data["name"]
    product.description = request.data["description"]
    product.price = request.data["price"]
    product.category = request.data["category"]
    product.brand = request.data["brand"]
    product.ratings = request.data["ratings"]
    product.stock = request.data["stock"]

    product.save()

    serializer = ProductSerializer(product, many=False)

    return Response({"product": serializer.data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    """Delete Product by it's ID"""
    product = get_object_or_404(Product, id=pk)

    # Check if the user is the owner of the product
    if product.user != request.user:
        return Response({
            "error": "Only the owner of the product can delete this"
            },
                        status=status.HTTP_403_FORBIDDEN
                        )

    args = {"product": pk}
    images = ProductImages.objects.filter(**args)
    for i in images:
        i.delete()

    product.delete()

    return Response({"details": "Product is deleted"},
                    status=status.HTTP_200_OK
                    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_single_image(request, pk):
    """Delete a Single Image from AWS Bucket by Image ID"""
    args = {"id": pk}
    image = ProductImages.objects.filter(**args)

    product_id = image[0].product.id
    product = get_object_or_404(Product, id=product_id)

    # Check if the user is the owner of the product
    if product.user != request.user:
        return Response({
            "error": "Only the owner of the product can delete this"
                        },
                        status=status.HTTP_403_FORBIDDEN
                        )

    image.delete()

    return Response({"details": "Image is deleted"},
                    status=status.HTTP_200_OK
                    )


@swagger_auto_schema(
    method="POST",
    request_body=openapi.Schema(
        type='object',
        properties={
            "rating": openapi.Schema(type='string'),
            "comment":  openapi.Schema(type='string')
        },
        required=["rating", "comment"]
    )
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_review(request, pk):
    """Create Product Review"""
    user = request.user
    product = get_object_or_404(Product, id=pk)
    data = request.data

    review = product.reviews.filter(user=user)

    if data["rating"] <= 0 or data["rating"] > 5:

        return Response({"error": "Please select a value between 1-5"},
                        status=status.HTTP_400_BAD_REQUEST
                        )

    elif review.exists():

        new_review = {"rating": data["rating"], "comment": data["comment"]}
        review.update(**new_review)

        rating = product.reviews.aggregate(avg_ratings=Avg("rating"))

        product.ratings = rating["avg_ratings"]
        product.save()

        return Response({"detail": "Review Updated"})

    else:

        Review.objects.create(
            user=user,
            product=product,
            rating=data["rating"],
            comment=data["comment"]
        )

        rating = product.reviews.aggregate(avg_ratings=Avg("rating"))

        product.ratings = rating["avg_ratings"]
        product.save()

        return Response({"detail": "New Review Created"})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_review(request, pk):
    """Delete Product Review"""
    user = request.user
    product = get_object_or_404(Product, id=pk)
    review = product.reviews.filter(user=user)

    if review.exists():

        review.delete()

        rating = product.reviews.aggregate(avg_ratings=Avg("rating"))

        if rating["avg_ratings"] is None:
            rating["avg_ratings"] = 0

        product.ratings = rating["avg_ratings"]
        product.save()

        return Response({"detail": "Review Deleted"})

    else:

        return Response({"detail": "Review Does Not Exist"},
                        status=status.HTTP_404_NOT_FOUND
                        )
