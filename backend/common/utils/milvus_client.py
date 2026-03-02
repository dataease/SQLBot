"""Milvus 向量数据库客户端封装"""
from typing import List, Optional, Dict, Any
from pymilvus import (
    connections, 
    Collection, 
    CollectionSchema, 
    FieldSchema, 
    DataType,
    utility,
    db as milvus_db
)
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


class MilvusClient:
    """Milvus 客户端单例"""
    _instance = None
    _connected = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._connected:
            self.connect()
    
    def connect(self):
        """连接到 Milvus，若目标 database 不存在则自动创建"""
        try:
            # 先连接到默认 database，以便执行 db 管理操作
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                user=settings.MILVUS_USER,
                password=settings.MILVUS_PASSWORD,
            )
            # 若目标 database 不存在则自动创建
            existing_dbs = milvus_db.list_database()
            if settings.MILVUS_DATABASE not in existing_dbs:
                SQLBotLogUtil.info(f"Milvus database '{settings.MILVUS_DATABASE}' not found, creating...")
                milvus_db.create_database(settings.MILVUS_DATABASE)
            # 切换到目标 database
            milvus_db.using_database(settings.MILVUS_DATABASE)
            self._connected = True
            SQLBotLogUtil.info("Milvus connection established")
        except Exception as e:
            SQLBotLogUtil.error(f"Failed to connect to Milvus: {e}")
            raise
    
    @staticmethod
    def create_collection(
        collection_name: str,
        dimension: int = 768,  # text2vec-base-chinese 的维度
        description: str = ""
    ) -> Collection:
        """
        创建 Milvus 集合
        
        Schema:
        - id: BigInt (主键)
        - embedding: FloatVector(dimension)
        - oid: BigInt (组织ID，用于多租户隔离)
        """
        full_name = collection_name
        
        # 检查集合是否已存在
        if utility.has_collection(full_name):
            SQLBotLogUtil.info(f"Collection {full_name} already exists")
            return Collection(full_name)
        
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="oid", dtype=DataType.INT64),  # 组织ID
        ]
        
        schema = CollectionSchema(fields=fields, description=description)
        collection = Collection(name=full_name, schema=schema)
        
        # 创建索引（使用 IVF_FLAT，适合中小规模数据）
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",  # 余弦相似度
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        
        SQLBotLogUtil.info(f"Created collection: {full_name}")
        return collection
    
    @staticmethod
    def insert_vectors(
        collection_name: str,
        ids: List[int],
        embeddings: List[List[float]],
        oids: List[int]
    ):
        """插入向量"""
        full_name = collection_name
        collection = Collection(full_name)
        
        data = [ids, embeddings, oids]
        collection.insert(data)
        collection.flush()
    
    @staticmethod
    def search_vectors(
        collection_name: str,
        query_embedding: List[float],
        oid: int,
        top_k: int = 10,
        similarity_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        搜索向量
        
        返回格式: [{"id": 123, "similarity": 0.95}, ...]
        """
        full_name = collection_name
        collection = Collection(full_name)
        collection.load()
        
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        
        # 添加过滤条件：只搜索特定 oid 的数据
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=f"oid == {oid}",  # 过滤条件
            output_fields=["id"]
        )
        
        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                if hit.distance >= similarity_threshold:  # COSINE 相似度，越大越相似
                    formatted_results.append({
                        "id": hit.id,
                        "similarity": float(hit.distance)
                    })
        
        return formatted_results
    
    @staticmethod
    def delete_vectors(collection_name: str, ids: List[int]):
        """删除向量"""
        full_name = collection_name
        collection = Collection(full_name)
        
        expr = f"id in {ids}"
        collection.delete(expr)
        collection.flush()
    
    @staticmethod
    def update_vectors(
        collection_name: str,
        ids: List[int],
        embeddings: List[List[float]],
        oids: List[int]
    ):
        """更新向量（先删除再插入）"""
        MilvusClient.delete_vectors(collection_name, ids)
        MilvusClient.insert_vectors(collection_name, ids, embeddings, oids)


# 全局实例
milvus_client = MilvusClient()