from pydantic import BaseModel
from tortoise import fields, models
from typing import Optional, Any, Union, TYPE_CHECKING
from tortoise.models import Model
from tortoise.queryset import QuerySet
from dotenv import load_dotenv

load_dotenv()

# 基础模型，包含创建时间和更新时间字段
# 该模型为抽象模型，不会在数据库中创建对应的表
# 其他具体模型继承该模型，可自动拥有 created_at 和 updated_at 字段
class TimeRecordModel(models.Model):
    # 记录数据创建的时间，在数据插入时自动设置为当前时间
    created_at = fields.DatetimeField(auto_now_add=True)
    # 记录数据更新的时间，在数据更新时自动更新为当前时间
    updated_at = fields.DatetimeField(auto_now=True)
    DoesNotExist = None

    class Meta:
        abstract = True


# 用户模型，用于数据库存储
# 表名：user
# 主键：id
# 外键：Patient or Doctor
class User(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True, auto_increment=True)
    # 用户名，最大长度为 50，唯一且添加索引，方便快速查找
    phone_number = fields.CharField(max_length=11, index=True)
    # 哈希后的密码，最大长度为 128
    hashed_password = fields.CharField(max_length=128)
    # 头像
    image = fields.BinaryField(null=True)
    # 登录账号的病人身份状态，若登录为病人身份则为 True,否则为 False
    patient_status = fields.BooleanField(default=False)
    # 登录账号的医生身份状态，若登录为医生身份则为 True,否则为 False
    doctor_status = fields.BooleanField(default=False)
    # 病人账户
    patient = fields.ForeignKeyField('models.Patient', related_name='user', index=True, null=True)
    # 医生账户
    doctor = fields.ForeignKeyField('models.Doctor', related_name='user', index=True, null=True)


# Pydantic 用户数据基础信息模型
# 用于验证和传输用户基础信息，不对应数据库表
class UserBase(BaseModel):
    """pydantic 用户数据基础信息"""
    # 用户名
    phone_number: str


# Pydantic 用户数据创建信息模型
# 用于验证和传输用户创建信息，不对应数据库表
class UserCreate(UserBase):
    """pydantic 用户数据创建信息"""
    # 用户密码
    password: str


# Pydantic 返回给客户端的用户信息模型
# 用于将用户信息返回给客户端，不对应数据库表
class UserOut(UserBase):
    """pydantic 返回给客户端信息"""
    # 用户 ID
    id: int


# Pydantic 令牌模型
# 用于验证和传输令牌信息，不对应数据库表
class Token(BaseModel):
    # 访问令牌
    access_token: str
    # 令牌类型
    token_type: str


# 医生模型
# 表名：doctor
# 主键：id
class Doctor(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True, auto_increment=True)
    # 医生姓名，最大长度为 50，唯一且添加索引，方便快速查找
    name = fields.CharField(max_length=50, index=True, null=True)
    # 医生的专业工作号码
    profession_number = fields.CharField(max_length=50, unique=True, null=True, index=True)
    # 医生工龄，整数类型
    working_years = fields.IntField(min_value=0, max_value=100, null=True)
    # 医生手机号码，最大长度为 11
    phone_number = fields.CharField(max_length=11, null=True)
    # 医生性别，最大长度为 3
    gender = fields.CharField(max_length=3, null=True)
    # 医生所属医院，最大长度为 50
    hospital = fields.CharField(max_length=50, null=True)
    # 医生职称，最大长度为 50
    title = fields.CharField(max_length=50, null=True)
    # 医生预约量，默认为 0
    appointment_count = fields.IntField(min_value=0, max_value=100, default=0)
    # 医生挂号费，浮点数类型
    registration_fee = fields.FloatField(min_value=0, max_value=100000, null=True)
    # 医生简介，文本类型
    introduction = fields.TextField(null=True)
    # 医生擅长技术，文本类型
    expertise = fields.TextField(null=True)
    # 医生收款码，最大长度为 255
    payment_qr_code = fields.CharField(max_length=255, null=True)
    # 医生头像
    image = fields.BinaryField(null=True)


class DoctorInfo(BaseModel):
    id: int = None
    working_years: Optional[int] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    hospital: Optional[str] = None
    title: Optional[str] = None
    appointment_count: Optional[int] = None
    registration_fee: Optional[float] = None
    introduction: Optional[str] = None
    expertise: Optional[str] = None
    payment_qr_code: Optional[str] = None
    image: Optional[str] = None
    phone_number: Optional[str] = None
    profession_number: Optional[str] = None


class DoctorInfoOut(BaseModel):
    working_years: int
    name: str
    phone_number: str
    gender: str
    hospital: str
    title: str
    appointment_count: int
    registration_fee: float
    introduction: str
    expertise: str
    payment_qr_code: str


# 患者模型
# 表名：patient
# 主键：id
class Patient(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 患者姓名，最大长度为 50
    name = fields.CharField(max_length=50, null=True)
    # 患者年龄，整数类型
    age = fields.IntField(min_value=0, max_value=100, null=True)
    # 患者性别，最大长度为 10
    gender = fields.CharField(max_length=3, null=True)
    # 患者身份证号，最大长度为 20
    id_card = fields.CharField(max_length=20, null=True)
    # 患者婚姻状况，最大长度为 20
    marital_status = fields.CharField(max_length=20, null=True)
    # 患者民族，最大长度为 50
    ethnicity = fields.CharField(max_length=50, null=True)
    # 患者居住地，最大长度为 200
    residence = fields.CharField(max_length=200, null=True)
    # 患者出生日期，日期类型
    birth_date = fields.CharField(max_length=50, null=True)
    # 患者电话号码，最大长度为 20
    phone_number = fields.CharField(max_length=20, null=True)
    # 患者头像，最大长度为 255
    image = fields.BinaryField(null=True)


class PatientInfo(BaseModel):
    name: str = None
    age: str = None
    gender: str = None
    id_card: str = None
    marital_status: str = None
    ethnicity: str = None
    residence: str = None
    birth_date: str = None


# 病历模型
# 表名：medical_record
# 主键：id
# 外键：
# patient，关联 Patient 表的 id 字段
class MedicalRecord(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 关联的患者，外键，关联 Patient 表的 id 字段
    # related_name 用于通过 Patient 实例反向访问其病历记录
    patient = fields.ForeignKeyField('models.Patient', related_name='medical_records')
    # 关联的患者，外键，关联 Doctor 表的 id 字段
    # related_name 用于通过 Doctor 实例反向访问其病历记录
    # doctor = fields.ForeignKeyField('models.Doctor', related_name='medical_records')
    # 姓名
    name = fields.CharField(max_length=50, null=True)
    # 手机号
    phone_number = fields.CharField(max_length=11, null=True)
    # 性别
    gender = fields.CharField(max_length=3, null=True)
    # 年龄
    age = fields.IntField(min_value=0, max_value=100, null=True)
    # 患者病症描述，文本类型
    symptoms_description = fields.TextField(null=True)
    # 患者病症详细描述，文本类型
    detailed_description = fields.TextField(null=True)
    # 病情分析，文本类型
    condition_analysis = fields.TextField(null=True)
    # 药物推荐，文本类型
    drug_recommendation = fields.TextField(null=True)
    # 病历中的病症照片
    image = fields.BinaryField(null=True)


class MedicalRecordInfo(BaseModel):
    symptoms_description: Optional[str] = None
    detailed_description: Optional[str] = None
    condition_analysis: Optional[str] = None
    drug_recommendation: Any = None


# 预约单模型
# 表名：appointment
# 主键：id
# 外键：
# doctor，关联 Doctor 表的 id 字段；
# patient，关联 Patient 表的 id 字段；
# medical_record，关联 MedicalRecord 表的 id 字段
class Appointment(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 关联的医生，外键，关联 Doctor 表的 id 字段
    # related_name 用于通过 Doctor 实例反向访问其预约记录
    doctor = fields.ForeignKeyField('models.Doctor', related_name='appointments')
    # 关联的患者，外键，关联 Patient 表的 id 字段
    # related_name 用于通过 Patient 实例反向访问其预约记录
    patient = fields.ForeignKeyField('models.Patient', related_name='appointments')
    # 关联的病历，外键，关联 MedicalRecord 表的 id 字段，可为空
    # related_name 用于通过 MedicalRecord 实例反向访问其关联的预约记录
    medical_record = fields.ForeignKeyField('models.MedicalRecord', related_name='appointments', null=True)
    # 预约单号，最大长度为 20，唯一且添加索引，方便快速查找
    appointment_number = fields.CharField(max_length=100, unique=True, index=True)
    # 预约时间，日期时间类型
    appointment_time = fields.CharField(max_length=50, null=True)
    # 患者就诊时间，日期时间类型
    patient_visit_time = fields.CharField(max_length=50, null=True)


class Reservation(BaseModel):
    appointment_time: Optional[str] = None
    doctor_id: Union[int, str] = None


class AppointmentInfo(BaseModel):
    appointment_number: Optional[str] = None
    appointment_time: Optional[str] = None
    patient_visit_time: Optional[str] = None


# 医患单模型
# 表名：doctor_patient_form
# 主键：id
# 外键：
# doctor，关联 Doctor 表的 id 字段；
# patient，关联 Patient 表的 id 字段
class DoctorPatientForm(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 关联的医生，外键，关联 Doctor 表的 id 字段
    # related_name 用于通过 Doctor 实例反向访问其医患单记录
    doctor = fields.ForeignKeyField('models.Doctor', related_name='doctor_patient_forms')
    # 关联的患者，外键，关联 Patient 表的 id 字段
    # related_name 用于通过 Patient 实例反向访问其医患单记录
    patient = fields.ForeignKeyField('models.Patient', related_name='doctor_patient_forms')
    # 诊治建议
    cure_suggestion = fields.TextField(null=True)
    # 时间
    time_record = fields.CharField(max_length=100, index=True)


# 帖子模型
# 表名：post
# 主键：id
# 外键：
# author，关联 User 表的 id 字段
class Post(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 帖子标题，最大长度为 100
    title = fields.CharField(max_length=100, index=True)
    # 帖子分类，最大长度为 50
    category = fields.CharField(max_length=50, index=True)
    # 帖子内容
    description = fields.TextField()
    # 帖子图片
    image = fields.BinaryField(null=True)
    # 帖子作者，外键，关联 User 表的 id 字段
    # related_name 用于通过 User 实例反向访问其发布的帖子记录
    author = fields.ForeignKeyField('models.User', related_name='posts', on_delete=fields.CASCADE)

    class Meta:
        table = 'post'
        ordering = ['-created_at']


class PostInfo(BaseModel):
    title: str
    category: str
    description: str
    image: str | None = None


# 评论模型
# 表名：comment
# 主键：id
# 外键：
# post，关联 Post 表的 id 字段；
# user，关联 User 表的 id 字段
class Comment(TimeRecordModel):
    # 主键，自增整数类型
    id = fields.IntField(pk=True)
    # 关联的帖子，外键，关联 Post 表的 id 字段
    # related_name 用于通过 Post 实例反向访问其评论记录
    post = fields.ForeignKeyField('models.Post', related_name='comments', on_delete=fields.CASCADE)
    # 评论用户，外键，关联 User 表的 id 字段
    # related_name 用于通过 User 实例反向访问其评论记录
    user = fields.ForeignKeyField('models.User', related_name='comments', on_delete=fields.CASCADE)
    # 评论内容，文本类型
    content = fields.TextField()
    # 评论图片
    image = fields.BinaryField(null=True)

    class Meta:
        table = 'comment'
        ordering = ['-created_at']


class CommentInfo(BaseModel):
    content: str
    image: str | None = None


# 照片模型，用于存储照片信息
class Photo(TimeRecordModel):
    id = fields.IntField(pk=True)  # 主键，自增整数
    title = fields.CharField(max_length=200, null=True)  # 照片标题
    image = fields.BinaryField(null=True)
    user = fields.ForeignKeyField('models.User', related_name='photos', on_delete=fields.CASCADE)  # 关联用户

    class Meta:
        table = 'photo'


class LikePost(Model):
    id = fields.IntField(pk=True)
    post = fields.ForeignKeyField('models.Post', related_name='likes', on_delete=fields.CASCADE)
    user = fields.ForeignKeyField('models.User', related_name='liked_posts', on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'like_post'
        unique_together = ('post', 'user')


class LikeComment(Model):
    id = fields.IntField(pk=True)
    comment = fields.ForeignKeyField('models.Comment', related_name='likes', on_delete=fields.CASCADE)
    user = fields.ForeignKeyField('models.User', related_name='liked_comments', on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'like_comment'
        unique_together = ('comment', 'user')



# 药物模型，继承自 TimeRecordModel，用于在数据库中存储药物的详细信息
class Drug(TimeRecordModel):
    # 药品的唯一标识符，最大长度为 20 个字符，在整个药物表中该值必须唯一，
    # 用于在数据库中准确区分不同的药物记录，便于进行查找、更新和删除等操作
    manualId = fields.CharField(max_length=20, unique=True)
    # 药品的通用名称，最大长度为 100 个字符，是被广泛认可和使用的药物名称，
    # 例如“阿司匹林肠溶片”，方便医护人员和患者识别药物
    genericName = fields.CharField(max_length=100)
    # 药品的剂量规格，最大长度为 50 个字符，明确了药物每次使用的剂量大小，
    # 如“50mg”，有助于指导用药
    strength = fields.CharField(max_length=50)
    # 药品的产地，最大长度为 50 个字符，表明药物的生产来源地，
    # 例如“国产”或具体的国家、地区名称
    origin = fields.CharField(max_length=50)
    # 药品的类型，最大长度为 50 个字符，用于区分药物所属的类别，
    # 如“西药”“中药”“生物制品”等
    drugType = fields.CharField(max_length=50)
    # 药品的主要成分名称，最大长度为 100 个字符，指出药物中起主要治疗作用的化学成分，
    # 例如“阿司匹林”
    ingredientName = fields.CharField(max_length=255)    # 药品的原始成分信息，使用文本类型存储，包含药物的化学名称、结构式、分子式等详细信息，
    # 为药物的研发、生产和质量控制提供依据
    originalIngredient = fields.TextField()

    # 药品的性状描述，使用文本类型存储，描述药物的外观、形态、颜色、气味等特征，
    # 如“本品为肠溶包衣片，除去包衣后显白色”，有助于识别药物的真伪和质量
    character = fields.TextField()

    # 药品的适应症，使用文本类型存储，说明药物可以治疗的疾病或症状，
    # 例如“镇痛、解热、抗炎、抗风湿等”，指导医生和患者合理用药
    indication = fields.TextField()

    # 药品的用法用量，使用文本类型存储，详细说明药物的使用方法（如口服、注射等）和剂量，
    # 如“成人常用量口服，一次 0.3 - 0.6g，一日 3 次”，确保用药安全有效
    usageAndDosage = fields.TextField()

    # 药品的不良反应，使用文本类型存储，列出使用药物可能出现的负面反应，
    # 例如“恶心、呕吐、胃肠道出血等”，让使用者提前了解风险
    adverseReactions = fields.TextField()

    # 药品的禁忌症，使用文本类型存储，明确哪些人群或情况不适合使用该药物，
    # 如“对本品过敏者禁用”，保障用药安全
    contraindication = fields.TextField()

    # 药品的警告信息，使用文本类型存储，提醒使用者在使用药物时需要特别注意的事项，
    # 例如“避免与其他非甾体抗炎药合并用药”，防止药物相互作用产生不良后果
    warning = fields.TextField()

    # 药品的注意事项，使用文本类型存储，提供使用药物时的一些额外注意要点，
    # 如“老年患者慎用”，帮助使用者正确用药
    precautions = fields.TextField()

    # 孕妇用药注意事项，使用文本类型存储，针对孕妇群体使用该药物的特殊说明，
    # 例如“本品易于通过胎盘，可能致畸”，保障孕妇和胎儿的安全
    pregnantRemarks = fields.TextField()

    # 儿童用药注意事项，使用文本类型存储，针对儿童群体使用该药物的特殊说明，
    # 如“小儿患者易出现毒性反应”，指导儿童合理用药
    childrenMedication = fields.TextField()

    # 老年用药注意事项，使用文本类型存储，针对老年群体使用该药物的特殊说明，
    # 例如“老年患者肾功能下降，易出现毒性反应”，考虑到老年人的生理特点
    elderlyMedication = fields.TextField()

    # 药品的相互作用，使用文本类型存储，说明该药物与其他药物同时使用时可能产生的相互影响，
    # 如“与抗凝药同用可增加出血风险”，避免联合用药的不良反应
    drugInteractions = fields.TextField()

    # 药品的过量反应，使用文本类型存储，描述药物使用过量时可能出现的症状，
    # 例如“轻度表现为头痛、头晕，重度可出现血尿、抽搐等”，便于及时处理过量用药情况
    overdose = fields.TextField()

    # 药品的药理作用，使用文本类型存储，解释药物在体内发挥作用的原理和机制，
    # 例如“镇痛、抗炎、解热、抗风湿等”，帮助理解药物的治疗效果
    pharmacology = fields.TextField()

    # 药品的毒理学信息，使用文本类型存储，提供药物的毒性相关信息，
    # 如“暂无”或具体的毒性数据，评估药物的安全性
    toxicology = fields.TextField()

    # 药品的药代动力学信息，使用文本类型存储，描述药物在体内的吸收、分布、代谢和排泄过程，
    # 例如“吸收、分布、代谢、排泄等”，为合理用药提供依据
    pharmacokinetics = fields.TextField()

    # 药品的储存条件，使用文本类型存储，说明药物保存的环境要求，
    # 如“密封，在干燥处保存”，保证药物的质量稳定
    storage = fields.TextField()

    # 药品的包装信息，使用文本类型存储，描述药物的包装形式和规格，
    # 如“铝塑包装，18 片/板×4 板/盒”，方便管理和使用
    packaging = fields.TextField()

    # 药品的有效期，最大长度为 50 个字符，表明药物在规定条件下保持质量的期限，
    # 如“24 个月”，提醒使用者在有效期内使用药物
    validity = fields.CharField(max_length=50)


# 疾病模型，继承自 TimeRecordModel，用于在数据库中存储疾病的相关信息
class Disease(Model):
    # 疾病的名称，最大长度为 100 个字符，在整个疾病表中该值必须唯一，
    # 用于准确标识不同的疾病，如“痤疮和酒渣鼻”
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)

    if TYPE_CHECKING:
        recommended_drugs: QuerySet['DiseaseDrugRecommendation']


# 疾病药物推荐关联模型，继承自 TimeRecordModel，用于建立疾病和推荐药物之间的关联关系
class DiseaseDrugRecommendation(Model):
    # 关联的疾病，通过外键关联到 Disease 模型，
    # related_name='recommended_drugs' 允许通过 Disease 实例反向访问推荐的药物列表
    disease = fields.ForeignKeyField('models.Disease', related_name='recommended_drugs')
    # 关联的药物，通过外键关联到 Drug 模型，
    # related_name='recommended_for_diseases' 允许通过 Drug 实例反向访问该药物被推荐用于治疗的疾病列表
    drug = fields.ForeignKeyField('models.Drug', related_name='recommended_for_diseases')


# Pydantic 药物信息模型，用于验证和处理药物信息的输入和输出
class DrugInfo(BaseModel):
    # 药品的唯一标识符，字符串类型，与 Drug 模型中的 manualId 对应
    manualId: str
    # 药品的通用名称，字符串类型，与 Drug 模型中的 genericName 对应
    genericName: str
    # 药品的剂量规格，字符串类型，与 Drug 模型中的 strength 对应
    strength: str
    # 药品的产地，字符串类型，与 Drug 模型中的 origin 对应
    origin: str
    # 药品的类型，字符串类型，与 Drug 模型中的 drugType 对应
    drugType: str
    # 药品的主要成分名称，字符串类型，与 Drug 模型中的 ingredientName 对应
    ingredientName: str
    # 药品的原始成分信息，字符串类型，与 Drug 模型中的 originalIngredient 对应
    originalIngredient: str
    # 药品的性状描述，字符串类型，与 Drug 模型中的 character 对应
    character: str
    # 药品的适应症，字符串类型，与 Drug 模型中的 indication 对应
    indication: str
    # 药品的用法用量，字符串类型，与 Drug 模型中的 usageAndDosage 对应
    usageAndDosage: str
    # 药品的不良反应，字符串类型，与 Drug 模型中的 adverseReactions 对应
    adverseReactions: str
    # 药品的禁忌症，字符串类型，与 Drug 模型中的 contraindication 对应
    contraindication: str
    # 药品的警告信息，字符串类型，与 Drug 模型中的 warning 对应
    warning: str
    # 药品的注意事项，字符串类型，与 Drug 模型中的 precautions 对应
    precautions: str
    # 孕妇用药注意事项，字符串类型，与 Drug 模型中的 pregnantRemarks 对应
    pregnantRemarks: str
    # 儿童用药注意事项，字符串类型，与 Drug 模型中的 childrenMedication 对应
    childrenMedication: str
    # 老年用药注意事项，字符串类型，与 Drug 模型中的 elderlyMedication 对应
    elderlyMedication: str
    # 药品的相互作用，字符串类型，与 Drug 模型中的 drugInteractions 对应
    drugInteractions: str
    # 药品的过量反应，字符串类型，与 Drug 模型中的 overdose 对应
    overdose: str
    # 药品的药理作用，字符串类型，与 Drug 模型中的 pharmacology 对应
    pharmacology: str
    # 药品的毒理学信息，字符串类型，与 Drug 模型中的 toxicology 对应
    toxicology: str
    # 药品的药代动力学信息，字符串类型，与 Drug 模型中的 pharmacokinetics 对应
    pharmacokinetics: str
    # 药品的储存条件，字符串类型，与 Drug 模型中的 storage 对应
    storage: str
    # 药品的包装信息，字符串类型，与 Drug 模型中的 packaging 对应
    packaging: str
    # 药品的有效期，字符串类型，与 Drug 模型中的 validity 对应
    validity: str
