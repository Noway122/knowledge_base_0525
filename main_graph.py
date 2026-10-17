import logging

from langgraph import graph
from langgraph.graph import StateGraph
from langgraph.graph import END

from processor.import_processor.nodes.a_node_entry import NodeEntry
from processor.import_processor.nodes.b_node_pdf_to_md import NodePDFToMD
from processor.import_processor.nodes.c_node_md_img import NodeMDImg
from processor.import_processor.nodes.d_node_document_split import NodeDocumentSplit
from processor.import_processor.nodes.e_node_item_name_recognition import NodeItemNameRecognition
from processor.import_processor.nodes.f_node_bge_embedding import NodeBGEEmbedding
from processor.import_processor.nodes.g_node_import_milvus import NodeImportMilvus
from processor.import_processor.state import ImportGraphState


class KBImportWorkflow:

    def __init__(self,config=None):
        self._compiled_graph = None

    @staticmethod
    def route_after_entry(state:ImportGraphState):
        # 修复：原 key 漏了尾字母 d（is_pdf_read_enable），与 state 实际字段名
        # （is_pdf_read_enabled / is_md_read_enabled）不一致，导致路由恒走 END
        if state.get("is_pdf_read_enabled"):
            return "b_node_pdf_to_md"
        elif state.get("is_md_read_enabled"):
            return "c_node_md_img"
        else:
            return END


    @property
    def graph(self):
        """
        返回图实例
        """
        if self._compiled_graph is None:
            self._compiled_graph = self.build_graph()#创建图

        logging.info("获取图实例")
        return self._compiled_graph

    def build_graph(self):
        """
        创建主图
        :return:
        """
        graph = StateGraph(ImportGraphState)

        #1.注册节点
        graph.add_node("a_node_entry",NodeEntry())
        graph.add_node("b_node_pdf_to_md",NodePDFToMD())
        graph.add_node("c_node_md_img",NodeMDImg())
        graph.add_node("d_node_document_split",NodeDocumentSplit())
        graph.add_node("e_node_item_name_recognition",NodeItemNameRecognition())
        graph.add_node("f_node_bge_embedding",NodeBGEEmbedding())
        graph.add_node("g_node_import_milvus",NodeImportMilvus())

        graph.set_entry_point("a_node_entry")#定义节点入口

        #2.注册边

        graph.add_edge("b_node_pdf_to_md","c_node_md_img")
        graph.add_edge("c_node_md_img","d_node_document_split")
        graph.add_edge("d_node_document_split","e_node_item_name_recognition")
        graph.add_edge("e_node_item_name_recognition","f_node_bge_embedding")
        graph.add_edge("f_node_bge_embedding","g_node_import_milvus")

        # 4. 注册条件边
        graph.add_conditional_edges(
            "a_node_entry",
            self.route_after_entry,
            {
                # key：路由函数的返回值，value:节点的名字
                "c_node_md_img": "c_node_md_img",
                "b_node_pdf_to_md": "b_node_pdf_to_md",
                END: END
            }
        )

        #3.编译图
        return graph.compile()

#4.运行图
    def run(self, state: ImportGraphState, stream: bool = False):

        if stream:
            # return self.graph.stream(state, stream_mode="values")
            return self.graph.stream(state)
        else:
            return self.graph.invoke(state)



if __name__ == "__main__":
    workflow = KBImportWorkflow()

    init_state = {"import_file_path":r"C:\Users\小黑\Desktop\掌柜智库\掌柜智库课件0525\2.资料\04-设备手册汇总\doc\Aolynk CC系列室内型Cable网络集中器 用户手册-6W202-整本手册.pdf",
                  "file_dir":r"D:\output"}
    for event in workflow.run(init_state,stream=True):
        print(f"state:{event}")