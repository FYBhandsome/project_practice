import logging, traceback
from typing import List
from fastapi import APIRouter, HTTPException
from tortoise.transactions import in_transaction
from models import Drug, Disease, DiseaseDrugRecommendation, DrugInfo
from tortoise.exceptions import DoesNotExist

router = APIRouter()


# 药物操作类保持不变
class DrugManager:
    @staticmethod
    async def add_drug(drug_info: DrugInfo):
        print("add_drug")
        try:
            drug = await Drug.create(
                manualId=drug_info.manualId,
                genericName=drug_info.genericName,
                strength=drug_info.strength,
                origin=drug_info.origin,
                drugType=drug_info.drugType,
                ingredientName=drug_info.ingredientName,
                originalIngredient=drug_info.originalIngredient,
                character=drug_info.character,
                indication=drug_info.indication,
                usageAndDosage=drug_info.usageAndDosage,
                adverseReactions=drug_info.adverseReactions,
                contraindication=drug_info.contraindication,
                warning=drug_info.warning,
                precautions=drug_info.precautions,
                pregnantRemarks=drug_info.pregnantRemarks,
                childrenMedication=drug_info.childrenMedication,
                elderlyMedication=drug_info.elderlyMedication,
                drugInteractions=drug_info.drugInteractions,
                overdose=drug_info.overdose,
                pharmacology=drug_info.pharmacology,
                toxicology=drug_info.toxicology,
                pharmacokinetics=drug_info.pharmacokinetics,
                storage=drug_info.storage,
                packaging=drug_info.packaging,
                validity=drug_info.validity
            )
            return drug
        except Exception as e:
            print(f"Error in add_drug: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error adding drug: {str(e)}")

    @staticmethod
    async def get_drug(manualId: str):
        print("get_drug")
        try:
            drug = await Drug.get(manualId=manualId)
            return drug
        except DoesNotExist:
            print("Drug not found in get_drug")
            raise HTTPException(status_code=404, detail="Drug not found")
        except Exception as e:
            print(f"Error in get_drug: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting drug: {str(e)}")

    @staticmethod
    async def partial_update_drug(manualId: str, **kwargs):
        print("partial_update_drug")
        try:
            drug = await Drug.get(manualId=manualId)
            for key, value in kwargs.items():
                if hasattr(drug, key):
                    setattr(drug, key, value)
            await drug.save()
            return drug
        except DoesNotExist:
            print("Drug not found in partial_update_drug")
            raise HTTPException(status_code=404, detail="Drug not found")
        except Exception as e:
            print(f"Error in partial_update_drug: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating drug: {str(e)}")

    @staticmethod
    async def delete_drug(manualId: str):
        print("delete_drug")
        try:
            drug = await Drug.get(manualId=manualId)
            await drug.delete()
            return {"message": "Drug deleted successfully"}
        except DoesNotExist:
            print("Drug not found in delete_drug")
            raise HTTPException(status_code=404, detail="Drug not found")
        except Exception as e:
            print(f"Error in delete_drug: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting drug: {str(e)}")

    @staticmethod
    def drug_to_drug_info(drug: Drug) -> DrugInfo:
        try:
            drug_info = DrugInfo(
                manualId=drug.manualId,
                genericName=drug.genericName,
                strength=drug.strength,
                origin=drug.origin,
                drugType=drug.drugType,
                ingredientName=drug.ingredientName,
                originalIngredient=drug.originalIngredient,
                character=drug.character,
                indication=drug.indication,
                usageAndDosage=drug.usageAndDosage,
                adverseReactions=drug.adverseReactions,
                contraindication=drug.contraindication,
                warning=drug.warning,
                precautions=drug.precautions,
                pregnantRemarks=drug.pregnantRemarks,
                childrenMedication=drug.childrenMedication,
                elderlyMedication=drug.elderlyMedication,
                drugInteractions=drug.drugInteractions,
                overdose=drug.overdose,
                pharmacology=drug.pharmacology,
                toxicology=drug.toxicology,
                pharmacokinetics=drug.pharmacokinetics,
                storage=drug.storage,
                packaging=drug.packaging,
                validity=drug.validity
            )
            print("drug_to_drug_info")
        except Exception as e:
            print(f"Error in drug_to_drug_info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error converting drug to drug_info: {str(e)}")

        return drug_info


# 疾病 - 药物推荐操作类，修改 get_recommended_drug 方法
class DiseaseDrugRecommendationManager:
    @staticmethod
    async def add_recommendation(disease_name: str, drug_manualId: str):
        print("add_recommendation")
        try:
            async with in_transaction():
                print(f"Starting add_recommendation for disease: {disease_name}, drug: {drug_manualId}")
                disease, _ = await Disease.get_or_create(name=disease_name)
                drug = await Drug.get(manualId=drug_manualId)
                recommendation = await DiseaseDrugRecommendation.create(
                    disease=disease,
                    drug=drug
                )
            return recommendation
        except DoesNotExist:
            print("Drug or disease not found in add_recommendation")
            raise HTTPException(status_code=404, detail="Drug or disease not found")
        except Exception as e:
            print(f"Error in add_recommendation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error adding recommendation: {str(e)}")

    @staticmethod
    async def get_recommended_drug(disease_name: str) -> List[DrugInfo]:
        print("get_recommended_drug")
        try:
            print(f"Starting get_recommended_drug for disease: {disease_name}")
            # 通过多表关联查询一次性获取对应疾病的所有药物信息
            drugs = await Drug.filter(
                recommended_for_diseases__disease__name=disease_name
            ).all()

            if not drugs:
                print("No recommended drug found for this disease")
                raise HTTPException(status_code=404, detail="No recommended drug found for this disease")

            drug_list = [DrugManager.drug_to_drug_info(drug) for drug in drugs]
            return drug_list
        except DoesNotExist:
            print("Disease not found in get_recommended_drug")
            raise HTTPException(status_code=404, detail="Disease not found")
        except Exception as e:
            print(f"Error getting recommended drug: {str(e)}")
            logging.debug(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error1 getting recommended drug: {str(e)}")


# 路由部分保持不变
@router.post("/add_drug/", operation_id="unique_add_drug_route", summary="添加药物")
async def add_drug(drug_info: DrugInfo):
    print("post方式 add_drug")
    return await DrugManager.add_drug(drug_info)


@router.get("/get_drug/{manualId}/", operation_id="unique_get_drug_route", summary="获取药物")
async def get_drug(manualId: str):
    print("get方式 get_drug")
    return await DrugManager.get_drug(manualId)


@router.post("/get_recommended_drug/", summary="获取推荐药物")
async def get_recommended_drug(disease_name: str):
    print("进入 get_recommended_drug 函数")
    try:
        print(f"个性化药物推荐：Starting route get_recommended_drug for disease: {disease_name}")
        drug = await DiseaseDrugRecommendationManager.get_recommended_drug(disease_name)
        return {"code": 200, "data2": drug}
    except HTTPException as e:
        print(f"HTTPException in route get_recommended_drug: {e.detail}")
        return {"code": e.status_code, "data1": {"message": e.detail}}
    except Exception as e:
        print(f"Unexpected error in route get_recommended_drug: {str(e)}")
        logging.error(f"Unexpected error: {str(e)}")
        return {"code": 500, "data": {"message": f"Unexpected error: {str(e)}"}}


@router.patch("/partial_update_drug/{manualId}/", operation_id="unique_partial_update_drug_route", summary="部分更新药物")
async def partial_update_drug(manualId: str, **kwargs):
    print("patch方式 partial_update_drug")
    return await DrugManager.partial_update_drug(manualId, **kwargs)


@router.post("/add_recommendation/", operation_id="unique_add_recommendation_route", summary="添加推荐药物")
async def add_recommendation(disease_name: str, drug_manualId: str):
    print("post方式 add_recommendation ")
    return await DiseaseDrugRecommendationManager.add_recommendation(disease_name, drug_manualId)


@router.delete("/delete_drug/{manualId}/", operation_id="unique_delete_drug_route", summary="删除药物")
async def delete_drug(manualId: str):
    print("delete方式 delete_drug")
    return await DrugManager.delete_drug(manualId)


# 查询相应的疾病描述
@router.post("/disease_description/", summary="查询疾病描述")
async def Disease_Description(disease_name: str):
    disease = await Disease.get(description=disease_name)
    return disease.description
