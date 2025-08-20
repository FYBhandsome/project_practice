from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Form, Query
from fastapi.responses import JSONResponse
from models import User, Post, Comment, PostInfo, CommentInfo, LikePost, LikeComment
from dotenv import load_dotenv

import os
import logging
from extra_function import get_current_user
import base64

router = APIRouter()
UPLOAD_DIR = "uploads"
load_dotenv()
# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}


def format_datetime(dt):
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# 统一异常处理
async def handle_exception(request, exc):
    logging.error(f"Exception occurred: {str(exc)}")
    return JSONResponse(
        status_code=getattr(exc, "status_code", 500),
        content={"code": getattr(exc, "status_code", 500), "data": {"message": str(exc)}}
    )



# 假设这是允许的文件类型检查函数
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 封装函数，处理文件上传并返回二进制数据
async def process_uploaded_file(file: UploadFile):
    if not allowed_file(file.filename):
        raise HTTPException(400, "文件类型不支持")
    try:
        content = await file.read()
        return content
    except Exception as e:
        raise HTTPException(500, f"读取文件时出错: {str(e)}")

@router.post("/posts/", summary="创建帖子")
async def create_post(
        title: str = Form(...),
        category: str = Form(...),
        description: str = Form(...),
        current_user: User = Depends(get_current_user),
        file: UploadFile = File(...)
):
    """创建新帖子"""
    if not allowed_file(file.filename):
        raise HTTPException(400, "文件类型不支持")
    try:
        image_content = await process_uploaded_file(file)

        # 创建帖子记录
        post = await Post.create(
            title=title,
            category=category,
            description=description,
            image=image_content,
            author=current_user
        )
        logging.info(f"User {current_user.id} created post {post.id}")

        # 将二进制图片数据转换为 Base64 编码的字符串
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        return {
            "code": 200,
            "data": {
                "id": post.id,
                "title": post.title,
                "category": post.category,
                "description": post.description,
                "image": image_base64
            }
        }
    except Exception as e:
        raise HTTPException(500, f"服务器错误: {str(e)}")


# 获取帖子列表
@router.get("/posts/", response_model=dict, summary="获取帖子列表")
async def get_posts(
        title: str = Query(None, description="按标题搜索"),
        category: str = Query(None, description="按类别搜索"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, description="每页数量")
):
    """
    获取帖子列表，支持分页和搜索
    :param title: 标题搜索关键字
    :param category: 类别搜索关键字
    :param page: 页码
    :param page_size: 每页数量
    :return: 帖子列表
    """
    try:
        query = Post.all().prefetch_related('author')
        if title:
            query = query.filter(title__icontains=title)
        if category:
            query = query.filter(category__icontains=category)

        total = await query.count()
        posts = await query.offset((page - 1) * page_size).limit(page_size)

        post_list = []
        for post in posts:
            # 将二进制图片数据转换为 Base64 编码的字符串
            if post.image:
                image_base64 = base64.b64encode(post.image).decode('utf-8')
            else:
                image_base64 = None

            post_data = {
                "id": post.id,
                "title": post.title,
                "category": post.category,
                "description": post.description,
                "image": image_base64,
                "author": {
                    "id": post.author.id,
                    "phone_number": post.author.phone_number
                },
                "created_at": format_datetime(post.created_at),
                "updated_at": format_datetime(post.updated_at),
                "like_count": await LikePost.filter(post=post).count()
            }
            post_list.append(post_data)

        return {"code": 200, "data": {"total": total, "posts": post_list}}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# 获取单个帖子及其评论的接口
@router.get("/posts/{post_id}/", response_model=dict, summary="获取帖子及其评论")
async def get_post(post_id: int):
    """
    获取单个帖子及其相关评论
    :param post_id: 帖子的 ID
    :return: 包含帖子信息和评论列表的字典
    """
    try:
        post = await Post.get(id=post_id).prefetch_related('comments', 'author')
        comments = await post.comments.all().prefetch_related('user')

        comment_list = []
        for comment in comments:
            comment_image_base64 = base64.b64encode(comment.image).decode('utf-8') if comment.image else None
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "image": comment_image_base64,
                "user": {
                    "id": comment.user.id,
                    "phone_number": comment.user.phone_number
                },
                "created_at": format_datetime(comment.created_at),
                "updated_at": format_datetime(comment.updated_at),
                "like_count": await LikeComment.filter(comment=comment).count()
            }
            comment_list.append(comment_data)

        post_image_base64 = base64.b64encode(post.image).decode('utf-8') if post.image else None
        post_data = {
            "id": post.id,
            "title": post.title,
            "category": post.category,
            "description": post.description,
            "image": post_image_base64,
            "author": {
                "id": post.author.id,
                "phone_number": post.author.phone_number
            },
            "created_at": format_datetime(post.created_at),
            "updated_at": format_datetime(post.updated_at),
            "comments": comment_list,
            "like_count": await LikePost.filter(post=post).count()
        }
        return {"code": 200, "data": post_data}
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 创建评论的接口
@router.post("/posts/{post_id}/comments/", summary="创建评论")
async def create_comment(post_id: int, comment_info: CommentInfo, current_user: User = Depends(get_current_user)):
    """
    为指定帖子创建评论
    :param post_id: 帖子的 ID
    :param comment_info: 评论信息
    :param current_user: 当前用户
    :return: 创建的评论对象
    """
    try:
        post = await Post.get(id=post_id)
        comment = await Comment.create(
            post=post,
            user=current_user,
            content=comment_info.content,
            image=comment_info.image
        )
        comment_image_base64 = base64.b64encode(comment.image).decode('utf-8') if comment.image else None
        logging.info(f"User {current_user.id} created comment {comment.id} on post {post.id}")
        return {
            "code": 200,
            "data": {
                "id": comment.id,
                "content": comment.content,
                "image": comment_image_base64,
                "user": {
                    "id": current_user.id,
                    "phone_number": current_user.phone_number
                },
                "post": {
                    "id": post.id,
                    "title": post.title
                },
                "created_at": format_datetime(comment.created_at),
                "updated_at": format_datetime(comment.updated_at),
                "like_count": await LikeComment.filter(comment=comment).count()
            }
        }
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 删除帖子的接口
@router.delete("/posts/{post_id}/", summary="删除帖子")
async def delete_post(post_id: int, current_user: User = Depends(get_current_user)):
    """
    删除指定帖子及其相关评论
    :param post_id: 帖子的 ID
    :param current_user: 当前用户
    :return: 删除成功的消息
    """
    try:
        post = await Post.get(id=post_id)
        if post.author.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to delete this post")
        await Comment.filter(post=post).delete()  # 先删除该帖子下的所有评论
        await LikePost.filter(post=post).delete()  # 删除帖子的点赞记录

        await post.delete()
        logging.info(f"User {current_user.id} deleted post {post_id}")
        return {"code": 200, "data": {"message": "Post deleted successfully"}}
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 更新帖子的接口
@router.put("/posts/{post_id}/", summary="更新帖子")
async def update_post(post_id: int, post_info: PostInfo, current_user: User = Depends(get_current_user),
                      file: UploadFile = File(None)):
    """
    更新指定帖子的信息
    :param post_id: 帖子的 ID
    :param post_info: 新的帖子信息
    :param current_user: 当前用户
    :return: 更新后的帖子对象
    """
    try:
        post = await Post.get(id=post_id)
        if post.author.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not allowed to update this post")

        post.title = post_info.title
        post.category = post_info.category
        post.description = post_info.description

        if file:
            # 检查文件类型
            if not allowed_file(file.filename):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")

            try:
                image_content = await process_uploaded_file(file)
                post.image = image_content
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        await post.save()
        post_image_base64 = base64.b64encode(post.image).decode('utf-8') if post.image else None
        logging.info(f"User {current_user.id} updated post {post_id}")
        return {
            "code": 200,
            "data": {
                "id": post.id,
                "title": post.title,
                "category": post.category,
                "description": post.description,
                "image": post_image_base64,
                "author": {
                    "id": post.author.id,
                    "phone_number": post.author.phone_number
                },
                "created_at": format_datetime(post.created_at),
                "updated_at": format_datetime(post.updated_at),
                "like_count": await LikePost.filter(post=post).count()
            }
        }
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 删除评论的接口
@router.delete("/comments/{comment_id}/", summary="删除评论")
async def delete_comment(comment_id: int, current_user: User = Depends(get_current_user)):
    """
    删除指定评论
    :param comment_id: 评论的 ID
    :param current_user: 当前用户
    :return: 删除成功的消息
    """
    try:
        comment = await Comment.get(id=comment_id)
        if comment.user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not allowed to delete this comment")
        await LikeComment.filter(comment=comment).delete()  # 删除评论的点赞记录
        await comment.delete()
        logging.info(f"User {current_user.id} deleted comment {comment_id}")
        return {"code": 200, "data": {"message": "Comment deleted successfully"}}
    except Comment.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 更新评论的接口
@router.put("/comments/{comment_id}/", summary="更新评论")
async def update_comment(comment_id: int, comment_info: CommentInfo,
                         current_user: User = Depends(get_current_user), file: UploadFile = File(None)):
    """
    更新指定评论的信息
    :param comment_id: 评论的 ID
    :param comment_info: 新的评论信息
    :param current_user: 当前用户
    :return: 更新后的评论对象
    """
    try:
        comment = await Comment.get(id=comment_id)
        if comment.user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not allowed to update this comment")

        comment.content = comment_info.content

        if file:
            # 检查文件类型
            if not allowed_file(file.filename):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")

            try:
                image_content = await process_uploaded_file(file)
                comment.image = image_content
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        await comment.save()
        comment_image_base64 = base64.b64encode(comment.image).decode('utf-8') if comment.image else None
        logging.info(f"User {current_user.id} updated comment {comment_id}")
        return {
            "code": 200,
            "data": {
                "id": comment.id,
                "content": comment.content,
                "image": comment_image_base64,
                "user": {
                    "id": comment.user.id,
                    "phone_number": comment.user.phone_number
                },
                "post": {
                    "id": comment.post.id,
                    "title": comment.post.title
                },
                "created_at": format_datetime(comment.created_at),
                "updated_at": format_datetime(comment.updated_at),
                "like_count": await LikeComment.filter(comment=comment).count()
            }
        }
    except Comment.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# 点赞帖子的接口
@router.post("/posts/{post_id}/like/", summary="点赞帖子")
async def like_post(post_id: int, current_user: User = Depends(get_current_user)):
    """
    点赞指定帖子
    :param post_id: 帖子的 ID
    :param current_user: 当前用户
    :return: 点赞成功的消息
    """
    try:
        post = await Post.get(id=post_id)
        like, created = await LikePost.get_or_create(post=post, user=current_user)
        if not created:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already liked this post")
        logging.info(f"User {current_user.id} liked post {post_id}")
        return {"code": 200, "data": {"message": "Post liked successfully"}}
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 取消点赞帖子的接口
@router.delete("/posts/{post_id}/like/", summary="取消点赞帖子")
async def unlike_post(post_id: int, current_user: User = Depends(get_current_user)):
    """
    取消点赞指定帖子
        """
    try:
        post = await Post.get(id=post_id)
        like = await LikePost.filter(post=post, user=current_user).first()
        if not like:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You haven't liked this post yet")
        await like.delete()
        logging.info(f"User {current_user.id} unliked post {post_id}")
        return {"code": 200, "data": {"message": "Post like removed successfully"}}
    except Post.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 点赞评论的接口
@router.post("/comments/{comment_id}/like/", summary="点赞评论")
async def like_comment(comment_id: int, current_user: User = Depends(get_current_user)):
    """
    点赞指定评论
    :param comment_id: 评论的 ID
    :param current_user: 当前用户
    :return: 点赞成功的消息
    """
    try:
        comment = await Comment.get(id=comment_id)
        like, created = await LikeComment.get_or_create(comment=comment, user=current_user)
        if not created:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already liked this comment")
        logging.info(f"User {current_user.id} liked comment {comment_id}")
        return {"code": 200, "data": {"message": "Comment liked successfully"}}
    except Comment.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 取消点赞评论的接口
@router.delete("/comments/{comment_id}/like/", summary="取消点赞评论")
async def unlike_comment(comment_id: int, current_user: User = Depends(get_current_user)):
    """
    取消点赞指定评论
    :param comment_id: 评论的 ID
    :param current_user: 当前用户
    :return: 取消点赞成功的消息
    """
    try:
        comment = await Comment.get(id=comment_id)
        like = await LikeComment.filter(comment=comment, user=current_user).first()
        if not like:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You haven't liked this comment yet")
        await like.delete()
        logging.info(f"User {current_user.id} unliked comment {comment_id}")
        return {"code": 200, "data": {"message": "Comment like removed successfully"}}
    except Comment.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取用户点赞的帖子列表
@router.get("/users/{user_id}/liked-posts/", response_model=dict, summary="获取用户点赞的帖子列表")
async def get_user_liked_posts(
        user_id: int,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, description="每页数量")
):
    """
    获取指定用户点赞的帖子列表，支持分页
    :param user_id: 用户的 ID
    :param page: 页码
    :param page_size: 每页数量
    :return: 用户点赞的帖子列表
    """
    try:
        user = await User.get(id=user_id)
        liked_posts_query = LikePost.filter(user=user).prefetch_related('post__author')
        total = await liked_posts_query.count()
        liked_posts = await liked_posts_query.offset((page - 1) * page_size).limit(page_size)

        post_list = []
        for like in liked_posts:
            post = like.post
            post_data = {
                "id": post.id,
                "title": post.title,
                "category": post.category,
                "description": post.description,
                "image": post.image,
                "author": {
                    "id": post.author.id,
                    "phone_number": post.author.phone_number
                },
                "created_at": format_datetime(post.created_at),
                "updated_at": format_datetime(post.updated_at),
                "like_count": await LikePost.filter(post=post).count()
            }
            post_list.append(post_data)

        return {"code": 200, "data": {"total": total, "posts": post_list}}
    except User.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取用户点赞的评论列表
@router.get("/users/{user_id}/liked-comments/", response_model=dict, summary="获取用户点赞的评论列表")
async def get_user_liked_comments(
        user_id: int,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, description="每页数量")
):
    """
    获取指定用户点赞的评论列表，支持分页
    :param user_id: 用户的 ID
    :param page: 页码
    :param page_size: 每页数量
    :return: 用户点赞的评论列表
    """
    try:
        user = await User.get(id=user_id)
        liked_comments_query = LikeComment.filter(user=user).prefetch_related('comment__user', 'comment__post')
        total = await liked_comments_query.count()
        liked_comments = await liked_comments_query.offset((page - 1) * page_size).limit(page_size)

        comment_list = []
        for like in liked_comments:
            comment = like.comment
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "image": comment.image,
                "user": {
                    "id": comment.user.id,
                    "phone_number": comment.user.phone_number
                },
                "post": {
                    "id": comment.post.id,
                    "title": comment.post.title
                },
                "created_at": format_datetime(comment.created_at),
                "updated_at": format_datetime(comment.updated_at),
                "like_count": await LikeComment.filter(comment=comment).count()
            }
            comment_list.append(comment_data)

        return {"code": 200, "data": {"total": total, "comments": comment_list}}
    except User.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
