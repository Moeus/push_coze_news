from qiniu import Auth, put_file, etag
#需要填写你的 Access Key 和 Secret Key
#构建鉴权对象
q = Auth(access_key="FZzEtGwpcOqeY4TgSreLMjMZ0KmzOXfPlFSQfPRY", secret_key="qFWi1wp8H4HAkmXH1gRAd3xDh8ZlyKUF3jVaDyQH")

#要上传的空间
bucket_name = 'moeus-news-png'
#上传后保存的文件名
key = '2025-3-7.png'
#生成上传 Token，可以指定过期时间等
token = q.upload_token(bucket_name, key, 3600)
#要上传文件的本地路径
localfile = r'D:\news_wechat_api\png\2025-3-7.png'
ret, info = put_file(token, key, localfile, version='v2')
print(info)
assert ret['key'] == key
assert ret['hash'] == etag(localfile)
print(ret)